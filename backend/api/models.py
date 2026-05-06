from django.db import models

class Document(models.Model):
    FILE_TYPES = (
        ('pdf', 'PDF'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('other', 'Other'),
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    summary = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

class Transcription(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='transcriptions')
    text = models.TextField()
    start_time = models.FloatField(help_text="Start time in seconds", null=True, blank=True)
    end_time = models.FloatField(help_text="End time in seconds", null=True, blank=True)
    topic = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Transcription for {self.document.title} at {self.start_time}s"

class ChatMessage(models.Model):
    ROLES = (
        ('user', 'User'),
        ('ai', 'AI'),
    )
    role = models.CharField(max_length=10, choices=ROLES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    # The referenced document/timestamp if the AI suggests jumping to a video part
    referenced_document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True)
    referenced_timestamp = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
