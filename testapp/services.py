import os
import openai
from django.conf import settings
from .models import Conversation, Message

class ChatbotService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        openai.api_key = self.api_key
        
    def get_chat_response(self, user, message_text, conversation_id=None):
        """
        Get a response from the OpenAI API and save the conversation
        """
        # Get or create conversation
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=user)
            except Conversation.DoesNotExist:
                conversation = Conversation.objects.create(user=user)
        else:
            conversation = Conversation.objects.create(user=user)
        
        # Save user message
        user_message = Message.objects.create(
            conversation=conversation,
            content=message_text,
            is_user=True
        )
        
        # Get conversation history (last 10 messages)
        history = conversation.messages.order_by('created_at')[:10]
        
        # Format messages for OpenAI
        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        
        for msg in history:
            role = "user" if msg.is_user else "assistant"
            messages.append({"role": role, "content": msg.content})
        
        # If the user's newest message isn't in history yet, add it
        if user_message not in history:
            messages.append({"role": "user", "content": message_text})
        
        try:
            # Call OpenAI API
            response = openai.chat.completions.create(
                model="gpt-4o-mini",  # or any other model you prefer
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )
            
            # Extract response text
            bot_response = response.choices[0].message.content.strip()
            
            # Save bot response
            bot_message = Message.objects.create(
                conversation=conversation,
                content=bot_response,
                is_user=False
            )
            
            return {
                "conversation_id": conversation.id,
                "message": bot_response
            }
            
        except Exception as e:
            # Handle errors
            error_message = f"Sorry, I encountered an error: {str(e)}"
            Message.objects.create(
                conversation=conversation,
                content=error_message,
                is_user=False
            )
            return {
                "conversation_id": conversation.id,
                "message": error_message
            }