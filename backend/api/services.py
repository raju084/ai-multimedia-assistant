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

def process_audio_video(document_instance):
    """
    Extracts transcription and timestamps from audio/video using Whisper.
    """
    file_path = document_instance.file.path
    
    # Load the base Whisper model (or use API if preferred)
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    
    # Save transcriptions with timestamps
    for segment in result['segments']:
        Transcription.objects.create(
            document=document_instance,
            text=segment['text'],
            start_time=segment['start'],
            end_time=segment['end'],
        )
    return result['text']

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
                f"When answering, if the {contentType} has timestamps (e.g. [12.5s]), find the most relevant timestamp "
                "where the answer is discussed and include it at the end of your response in the format: "
                "TIMESTAMP: {seconds}. Example: 'TIMESTAMP: 45.2'.\n\n"
                f"{contentType.capitalize()}:\n{timestamped_context[:15000]}"
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
                match = re.search(r"TIMESTAMP:\s*(\d+\.?\d*)", content)
                if match:
                    timestamp = float(match.group(1))
                    # Clean the tag out of the visible message
                    content = re.sub(r"TIMESTAMP:\s*\d+\.?\d*", "", content).strip()

            return content, timestamp
        except Exception as e:
            print(f"AI ERROR: {str(e)}")
            return f"Error communicating with AI: {str(e)}", None
    else:
        # Fallback: Mock AI
        if not context:
            return f"I couldn't find any content for '{document.title}' to analyze.", None
        return f"[MOCK AI] Based on the content of {document.title}: I can see you're asking about '{user_query}'. Please add a GROQ_API_KEY to your .env file to enable real AI responses.", None

