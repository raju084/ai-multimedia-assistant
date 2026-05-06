import os
import whisper
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .models import Transcription

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

_whisper_model = None

def get_whisper_model():
    """
    Lazy load the Whisper model to avoid repeated loading overhead.
    """
    global _whisper_model
    if _whisper_model is None:
        print("Loading Whisper 'base' model...")
        import whisper
        _whisper_model = whisper.load_model("base")
    return _whisper_model

def process_audio_video(document_instance):
    """
    Extracts transcription and timestamps from audio/video using Whisper.
    """
    file_path = document_instance.file.path
    print(f"Starting transcription for: {file_path}")
    
    try:
        # Load the base Whisper model
        model = get_whisper_model()
        result = model.transcribe(file_path)
        
        # Save transcriptions with timestamps
        transcription_objs = []
        for segment in result['segments']:
            transcription_objs.append(Transcription(
                document=document_instance,
                text=segment['text'].strip(),
                start_time=segment['start'],
                end_time=segment['end'],
            ))
        
        # Bulk create for efficiency
        Transcription.objects.bulk_create(transcription_objs)
        print(f"Transcription completed for: {document_instance.title}")
        return result['text']
    except Exception as e:
        print(f"TRANSCRIPTION ERROR for {document_instance.title}: {str(e)}")
        # Optionally, create a dummy transcription to indicate failure
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

