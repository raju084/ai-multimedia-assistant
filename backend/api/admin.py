from django.contrib import admin
from .models import Document, Transcription, ChatMessage

class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'file_type', 'uploaded_at')
    search_fields = ('title', 'file_type')
    list_filter = ('file_type', 'uploaded_at')

class TranscriptionAdmin(admin.ModelAdmin):
    list_display = ('document', 'start_time', 'end_time', 'topic')
    search_fields = ('text', 'topic', 'document__title')

class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('role', 'timestamp', 'referenced_document')
    list_filter = ('role', 'timestamp')

admin.site.register(Document, DocumentAdmin)
admin.site.register(Transcription, TranscriptionAdmin)
admin.site.register(ChatMessage, ChatMessageAdmin)
