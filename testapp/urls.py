from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name = 'home'),
    path('signup/', views.signup_view, name = 'signup'),
    path('login/', views.login_view, name = 'login'),
    path('logout/', views.logout_view, name = 'logout'),
    path('chat/', views.chat_view, name='chat'),

    # API endpoints
    path('api/register/', views.RegisterAPI.as_view(), name='api_register'),
    path('api/login/', views.LoginAPI.as_view(), name='api_login'),
    path('api/user/', views.user_detail, name='user_detail'),
    path('api/profile/update/', views.ProfileUpdateAPI.as_view(), name='profile_update'),

        # Chatbot API endpoints
    path('api/chat/message/', views.chat_message, name='chat_message'),
    path('api/chat/conversations/', views.get_conversations, name='get_conversations'),
    path('api/chat/conversations/<int:conversation_id>/', views.get_conversation, name='get_conversation_detail'),
    path('api/chat/conversations/new/', views.create_conversation, name='create_conversation'),
]