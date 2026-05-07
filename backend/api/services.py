import os
import math
import subprocess
import tempfile
import groq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .models import Transcription

# Groq Whisper API file size limit (25 MB). We use 20 MB per chunk to be safe.
GROQ_MAX_BYTES = 20 * 1024 * 1024  # 20 MB


def _get_audio_duration_seconds(file_path):
    """
    Returns the total duration of an audio/video file in seconds using ffprobe.
    Returns None if ffprobe is unavailable or fails.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"DEBUG: ffprobe check failed: {str(e)}")
        return None


def _split_audio_with_ffmpeg(file_path, chunk_duration_sec=600):
    """
    Splits a media file into chunks of `chunk_duration_sec` seconds each.
    Returns a list of (tmp_file_path, start_offset_seconds) tuples.
    Caller is responsible for deleting the tmp files.
    """
    total_duration = _get_audio_duration_seconds(file_path)
    if total_duration is None:
        # Cannot determine duration – return the original file as the only chunk
        return [(file_path, 0.0, False)]

    num_chunks = math.ceil(total_duration / chunk_duration_sec)
    chunks = []

    for i in range(num_chunks):
        start = i * chunk_duration_sec
        tmp = tempfile.NamedTemporaryFile(
            suffix=".mp3", delete=False, prefix=f"chunk_{i}_"
        )
        tmp_path = tmp.name
        tmp.close()

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-t", str(chunk_duration_sec),
            "-i", file_path,
            "-ar", "16000",   # 16 kHz mono – Whisper preferred
            "-ac", "1",
            "-q:a", "0",
            tmp_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=300)
        chunks.append((tmp_path, start, True))  # True = we own the file (delete it later)

    return chunks

# NOTE: Set OPENAI_API_KEY in your environment for Langchain OpenAI usage

def process_pdf(document_instance):
    """
    Extracts text from a PDF document using LangChain.
    """
    file_path = document_instance.file.path
    loader = PyPDFLoader(file_path)
    pages = loader.load_and_split()
    
    full_text = "\n".join([page.page_content for page in pages])
    
    # Save as transcription
    Transcription.objects.create(
        document=document_instance,
        text=full_text,
    )
    return full_text

def _transcribe_single_chunk(client, chunk_path, time_offset):
    """
    Sends one audio chunk to Groq Whisper and returns a list of Transcription-ready dicts
    with timestamps adjusted by `time_offset` seconds.
    """
    with open(chunk_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(chunk_path), f.read()),
            model="whisper-large-v3",
            response_format="verbose_json",
        )

    results = []
    segments = getattr(transcription, 'segments', [])
    for segment in segments:
        results.append({
            'text': segment['text'].strip(),
            'start': segment['start'] + time_offset,
            'end': segment['end'] + time_offset,
        })

    # Fallback: no segments but text present
    if not results and getattr(transcription, 'text', None):
        results.append({
            'text': transcription.text,
            'start': time_offset,
            'end': time_offset,
        })

    return results


def process_audio_video(document_instance):
    """
    Extracts transcription and timestamps from audio/video using Groq's Whisper API.
    Large files (>20 MB) are automatically split into chunks with ffmpeg so they
    never exceed Groq's 25 MB per-request limit.
    """
    file_path = document_instance.file.path
    print(f"Starting Groq transcription for: {file_path}")

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables.")

    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)

        file_size = os.path.getsize(file_path)
        all_segments = []

        if file_size <= GROQ_MAX_BYTES:
            # ── Fast path: file fits within Groq's limit ──────────────────────
            print(f"  File is {file_size / 1024 / 1024:.1f} MB — sending directly to Groq.")
            all_segments = _transcribe_single_chunk(client, file_path, time_offset=0.0)
        else:
            # ── Chunked path: split with ffmpeg then transcribe piece by piece ──
            print(
                f"  File is {file_size / 1024 / 1024:.1f} MB — "
                f"splitting into chunks for Groq (limit {GROQ_MAX_BYTES // 1024 // 1024} MB)."
            )
            chunks = _split_audio_with_ffmpeg(file_path, chunk_duration_sec=600)
            for idx, (chunk_path, time_offset, owned) in enumerate(chunks):
                print(f"  Transcribing chunk {idx + 1}/{len(chunks)} (offset={time_offset:.0f}s) …")
                try:
                    segments = _transcribe_single_chunk(client, chunk_path, time_offset)
                    all_segments.extend(segments)
                finally:
                    if owned:
                        try:
                            os.remove(chunk_path)
                        except OSError:
                            pass

        # ── Persist to database ───────────────────────────────────────────────
        transcription_objs = [
            Transcription(
                document=document_instance,
                text=seg['text'],
                start_time=seg['start'],
                end_time=seg['end'],
            )
            for seg in all_segments
        ]

        if not transcription_objs:
            Transcription.objects.create(
                document=document_instance,
                text="[No speech detected in the file.]",
                start_time=0.0,
                end_time=0.0,
            )
        else:
            Transcription.objects.bulk_create(transcription_objs)

        full_text = " ".join(seg['text'] for seg in all_segments)
        print(f"Groq transcription completed for: {document_instance.title}")
        return full_text

    except Exception as e:
        print(f"GROQ TRANSCRIPTION ERROR for {document_instance.title}: {str(e)}")
        Transcription.objects.create(
            document=document_instance,
            text=f"[Transcription Error: {str(e)}]",
        )
        raise e

def generate_ai_response(document, user_query):
    """
    Generates a response using document context.
    """
    # Fetch all transcriptions for this document
    transcriptions = Transcription.objects.filter(document=document).order_by('start_time')
    context = "\n".join([t.text for t in transcriptions])
    
    # Check for API keys
    groq_api_key = os.getenv("GROQ_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if groq_api_key or openai_api_key:
        try:
            if groq_api_key:
                from langchain_groq import ChatGroq
                chat = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.3-70b-versatile")
            else:
                from langchain_openai import ChatOpenAI
                chat = ChatOpenAI(openai_api_key=openai_api_key)

            from langchain_core.messages import HumanMessage, SystemMessage
            
            # Format transcript with timestamps for the AI
            timestamped_context = ""
            for t in transcriptions:
                time_str = f"[{t.start_time:.2f}s]" if t.start_time is not None else ""
                timestamped_context += f"{time_str} {t.text}\n"

            contentType = "transcript" if document.file_type in ['audio', 'video'] else "content"
            
            system_prompt = (
                f"You are a helpful assistant analyzing the {contentType} of '{document.title}'.\n"
                f"The provided {contentType} includes timestamps in brackets, like [12.50s].\n"
                "Your goal is to answer the user's question accurately based ONLY on the provided content.\n"
                "When you find the relevant part of the content, you MUST include the exact timestamp "
                "where it is discussed at the very end of your response.\n"
                "Format the timestamp as: TIMESTAMP: {seconds}\n"
                "Example: 'The speaker mentions the Game of Life at the beginning. TIMESTAMP: 5.2'\n\n"
                f"If you cannot find a specific timestamp or the transcript is empty, do not guess.\n\n"
                f"{contentType.capitalize()} Content:\n{timestamped_context[:15000]}"
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_query)
            ]
            response = chat.invoke(messages)
            content = response.content

            # Parse timestamp if present
            timestamp = None
            if "TIMESTAMP:" in content:
                import re
                match = re.search(r"TIMESTAMP:\s*(\d+\.?\d*)s?", content)
                if match:
                    timestamp = float(match.group(1))
                    # Clean the tag out of the visible message
                    content = re.sub(r"TIMESTAMP:\s*\d+\.?\d*\s*s?", "", content).strip()

            return content, timestamp
        except Exception as e:
            print(f"AI ERROR: {str(e)}")
            return f"Error communicating with AI: {str(e)}", None
    else:
        # Fallback: Mock AI
        if not context:
            return f"I couldn't find any content for '{document.title}' to analyze.", None
        return f"[MOCK AI] Based on the content of {document.title}: I can see you're asking about '{user_query}'. Please add a GROQ_API_KEY to your .env file to enable real AI responses.", None

