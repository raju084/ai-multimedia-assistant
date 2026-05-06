from rest_framework import viewsets, parsers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Document, ChatMessage
from .serializers import DocumentSerializer, ChatMessageSerializer
from api.services import process_pdf, process_audio_video

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser)

    def create(self, request, *args, **kwargs):
        from django.db import transaction
        import threading

        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            document = serializer.save()
        
        def run_processing(doc_id, file_type):
            from .models import Document
            from api.services import process_pdf, process_audio_video
            try:
                # Fetch a fresh copy in the thread
                doc = Document.objects.get(id=doc_id)
                if file_type == 'pdf':
                    process_pdf(doc)
                elif file_type in ['audio', 'video']:
                    process_audio_video(doc)
            except Exception as e:
                print(f"Background processing error: {str(e)}")

        # Start processing in a separate thread
        thread = threading.Thread(target=run_processing, args=(document.id, document.file_type))
        thread.start()
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        document = self.get_object()
        import threading
        from api.services import process_pdf, process_audio_video

        # Delete existing transcriptions
        document.transcriptions.all().delete()

        def run_processing(doc_id, file_type):
            from .models import Document
            try:
                doc = Document.objects.get(id=doc_id)
                if file_type == 'pdf':
                    process_pdf(doc)
                elif file_type in ['audio', 'video']:
                    process_audio_video(doc)
            except Exception as e:
                print(f"Background reprocessing error: {str(e)}")

        thread = threading.Thread(target=run_processing, args=(document.id, document.file_type))
        thread.start()

        return Response({'status': 'Reprocessing started'}, status=status.HTTP_202_ACCEPTED)

class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all().order_by('timestamp')
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        doc_id = self.request.query_params.get('document_id')
        if doc_id:
            queryset = queryset.filter(referenced_document_id=doc_id)
        return queryset

    def create(self, request, *args, **kwargs):
        # Save user message
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_message = serializer.save()

        # Generate AI response
        ai_content, timestamp = "I'm not sure which document you're referring to. Please select one.", None
        
        if user_message.referenced_document:
            from api.services import generate_ai_response
            ai_content, timestamp = generate_ai_response(
                user_message.referenced_document, 
                user_message.content
            )

        ai_response = ChatMessage.objects.create(
            role='ai',
            content=ai_content,
            referenced_document=user_message.referenced_document,
            referenced_timestamp=timestamp
        )
        
        ai_serializer = self.get_serializer(ai_response)
        return Response(ai_serializer.data, status=status.HTTP_201_CREATED)
