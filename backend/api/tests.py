from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Document, Transcription, ChatMessage
from rest_framework import status
import unittest.mock as mock

class APITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.doc = Document.objects.create(
            title="test.pdf",
            file_type="pdf",
            file=SimpleUploadedFile("test.pdf", b"pdf content")
        )

    def test_document_list(self):
        response = self.client.get(reverse('document-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_document_delete(self):
        response = self.client.delete(reverse('document-detail', args=[self.doc.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Document.objects.count(), 0)

    @mock.patch('api.services.process_pdf')
    def test_document_upload(self, mock_process):
        pdf_file = SimpleUploadedFile("new.pdf", b"new content", content_type="application/pdf")
        response = self.client.post(reverse('document-list'), {
            'title': 'new.pdf',
            'file': pdf_file,
            'file_type': 'pdf'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Wait a moment for background thread if necessary, but here we mock it
        self.assertTrue(Document.objects.filter(title='new.pdf').exists())

    def test_chat_message_creation(self):
        response = self.client.post(reverse('chatmessage-list'), {
            'role': 'user',
            'content': 'Hello',
            'referenced_document': self.doc.id
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ChatMessage.objects.count(), 2) # User + AI echo/mock
        self.assertEqual(ChatMessage.objects.last().role, 'ai')

    def test_chat_history_filtering(self):
        ChatMessage.objects.create(role='user', content='test', referenced_document=self.doc)
        response = self.client.get(reverse('chatmessage-list'), {'document_id': self.doc.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_transcription_model(self):
        t = Transcription.objects.create(
            document=self.doc,
            text="transcription text",
            start_time=10.0,
            end_time=20.0
        )
        self.assertEqual(str(t), f"Transcription for {self.doc.title} at 10.0s")

    @mock.patch('os.getenv')
    def test_ai_response_mock_fallback(self, mock_getenv):
        mock_getenv.return_value = None # No API key
        from api.services import generate_ai_response
        content, ts = generate_ai_response(self.doc, "hello")
        self.assertIn("[MOCK AI]", content)
        self.assertIsNone(ts)

    @mock.patch('langchain_groq.ChatGroq')
    @mock.patch('os.getenv')
    def test_ai_response_groq(self, mock_getenv, mock_groq):
        mock_getenv.return_value = "fake_key"
        mock_chat = mock.Mock()
        mock_chat.invoke.return_value.content = "Answer TIMESTAMP: 15.5"
        mock_groq.return_value = mock_chat
        
        Transcription.objects.create(document=self.doc, text="hello world", start_time=15.0)
        
        from api.services import generate_ai_response
        content, ts = generate_ai_response(self.doc, "hello")
        self.assertEqual(ts, 15.5)
        self.assertNotIn("TIMESTAMP:", content)

    @mock.patch('api.services.PyPDFLoader')
    def test_process_pdf(self, mock_loader):
        mock_instance = mock_loader.return_value
        mock_instance.load_and_split.return_value = [
            mock.Mock(page_content="page 1 content"),
            mock.Mock(page_content="page 2 content")
        ]
        
        from api.services import process_pdf
        text = process_pdf(self.doc)
        
        self.assertIn("page 1 content", text)
        self.assertTrue(Transcription.objects.filter(document=self.doc).exists())

    @mock.patch('api.services.whisper.load_model')
    def test_process_audio_video(self, mock_load_model):
        mock_model = mock_load_model.return_value
        mock_model.transcribe.return_value = {
            'text': 'full text',
            'segments': [
                {'text': 'segment 1', 'start': 0.0, 'end': 5.0},
                {'text': 'segment 2', 'start': 5.0, 'end': 10.0}
            ]
        }
        
        from api.services import process_audio_video
        text = process_audio_video(self.doc)
        
        self.assertEqual(text, 'full text')
        self.assertEqual(Transcription.objects.filter(document=self.doc).count(), 2)
