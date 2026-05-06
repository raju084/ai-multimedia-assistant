# AI Multimedia Q&A Assistant

A full-stack application that allows users to upload PDFs, audio, and video files and interact with them using an AI assistant. The app features automatic transcription (Whisper), AI-powered Q&A (Llama 3 via Groq), and intelligent timestamp-based video jumping.

## 🌟 Key Features
- **Multimedia Support**: Upload and process PDFs, MP4s, and MP3s.
- **AI Chat**: Ask questions about your documents and get context-aware answers.
- **Smart Timestamps**: AI automatically finds relevant moments in videos/audio.
- **Instant Playback**: Click an AI-generated timestamp to jump directly to that part of the media.
- **Recent Files Management**: Easily switch between uploaded files and maintain separate chat histories.
- **Background Processing**: Heavy media files are transcribed in the background to ensure a smooth UI.

## 🛠️ Tech Stack
- **Frontend**: React.js, Lucide Icons, Axios, CSS3 (Vanilla)
- **Backend**: Django, Django REST Framework, SQLite
- **AI/ML**: LangChain, Groq (Llama 3), OpenAI Whisper, FFmpeg

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- [FFmpeg](https://ffmpeg.org/download.html) (for media processing)
- Groq API Key (get it at [console.groq.com](https://console.groq.com))

### Backend Setup
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `backend/` folder:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here (optional)
   ```
5. Run migrations and start the server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

### Frontend Setup
1. Navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## 🧪 Testing & Coverage
To run backend tests and generate a coverage report:
```bash
cd backend
coverage run manage.py test
coverage report
```

## 🔌 API Documentation
- `POST /api/documents/`: Upload a new document/media file.
- `GET /api/documents/`: List all uploaded files.
- `DELETE /api/documents/{id}/`: Delete a file.
- `POST /api/chat/`: Send a message to the AI (requires `referenced_document` ID).
- `GET /api/chat/?document_id={id}`: Get chat history for a specific file.

## 🎥 Walkthrough Video
[Your Video Link Here]
