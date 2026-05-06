from rest_framework import serializers
from .models import Document, Transcription, ChatMessage

class TranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcription
        fields = '__all__'

class DocumentSerializer(serializers.ModelSerializer):
    transcriptions = TranscriptionSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = '__all__'

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = '__all__'
