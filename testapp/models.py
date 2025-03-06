# Add these models to your existing models.py file
from django.db import models
from django.contrib.auth.models import User

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Conversation {self.id} - {self.user.username}"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    content = models.TextField()
    is_user = models.BooleanField(default=True)  # True if message is from user, False if from bot
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{'User' if self.is_user else 'Bot'}: {self.content[:50]}..."