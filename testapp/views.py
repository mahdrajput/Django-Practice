from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required


from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token  
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes  

from .services import ChatbotService
from .serializers import ChatMessageSerializer, ConversationSerializer
from .models import Conversation

from .serializers import UserSerializer, RegisterSerializer, LoginSerializer, ProfileUpdateSerializer

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Create your views here.

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Check if the passwords match
        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return render(request, "testapp/signup.html")
        
        if User.objects.filter(username = username).exists():
            messages.error(request, "Username already exists")
            return render(request, "testapp/signup.html")
        
        if User.objects.filter(email = email).exists():
            messages.error(request, "Email already exists")
            return render(request, "testapp/signup.html")
        
        # Create User

        user = User.objects.create_user(
            username = username,
            email = email,
            password = password1
        )

        messages.success(request, "Account created successfully")
        return redirect('login')
    return render(request, "testapp/signup.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            
            # Get or create token for the user
            token, created = Token.objects.get_or_create(user=user)
            
            # Store token in session for JavaScript to access
            request.session['auth_token'] = token.key
            
            messages.success(request, "Login successful")
            return redirect('chat')
        else:
            messages.error(request, "Invalid username or password")
    return render(request, "testapp/login.html")

def logout_view(request):
    logout(request)
    messages.success(request, "Logout successful")
    return redirect('login')

@login_required
def home_view(request):
    """Home view that requires login"""
    return render(request, "testapp/home.html")

@login_required
def chat_view(request):
    """Render the chat interface"""
    return render(request, "testapp/chat.html")


# API Views

class RegisterAPI(APIView):
    @swagger_auto_schema(
        request_body=RegisterSerializer,
        responses={
            201: openapi.Response(
                description="Successfully registered",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'username': openapi.Schema(type=openapi.TYPE_STRING),
                            'email': openapi.Schema(type=openapi.TYPE_STRING),
                        }),
                        'token': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Bad Request"
        },
        operation_description="Register a new user and return a token"
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginAPI(APIView):
    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                description="Successfully logged in",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'username': openapi.Schema(type=openapi.TYPE_STRING),
                            'email': openapi.Schema(type=openapi.TYPE_STRING),
                        }),
                        'token': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: "Invalid credentials"
        },
        operation_description="Login with username and password to get a token"
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
@swagger_auto_schema(
    method='get',
    responses={
        200: UserSerializer,
        401: "Unauthorized"
    },
    operation_description="Get authenticated user's details",
    manual_parameters=[
        openapi.Parameter(
            'Authorization',
            openapi.IN_HEADER,
            description="Token <your_token>",
            type=openapi.TYPE_STRING,
            required=True
        )
    ]
)
@api_view(['GET'])  
@permission_classes([IsAuthenticated])
def user_detail(request):
    """Get the current user's details"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

class ProfileUpdateAPI(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=ProfileUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Profile updated successfully",
                schema=UserSerializer
            ),
            400: "Bad Request",
            401: "Unauthorized"
        },
        operation_description="Update user profile information"
    )
    def put(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, 
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                UserSerializer(request.user).data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@swagger_auto_schema(
    method='post',
    request_body=ChatMessageSerializer,
    responses={
        200: openapi.Response(
            description="Chat response",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'conversation_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        400: "Bad Request",
        401: "Unauthorized"
    },
    operation_description="Send a message to the chatbot and get a response"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_message(request):
    """Send a message to the chatbot and get a response"""
    serializer = ChatMessageSerializer(data=request.data)
    
    if serializer.is_valid():
        chatbot = ChatbotService()
        response = chatbot.get_chat_response(
            user=request.user,
            message_text=serializer.validated_data['message'],
            conversation_id=serializer.validated_data.get('conversation_id')
        )
        return Response(response)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    responses={
        200: ConversationSerializer(many=True),
        401: "Unauthorized"
    },
    operation_description="Get all conversations for the current user"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversations(request):
    """Get all conversations for the current user"""
    conversations = Conversation.objects.filter(user=request.user).order_by('-created_at')
    serializer = ConversationSerializer(conversations, many=True)
    return Response(serializer.data)

@swagger_auto_schema(
    method='get',
    responses={
        200: ConversationSerializer,
        401: "Unauthorized",
        404: "Not Found"
    },
    operation_description="Get a specific conversation by ID"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation(request, conversation_id):
    """Get a specific conversation by ID"""
    try:
        conversation = Conversation.objects.get(id=conversation_id, user=request.user)
    except Conversation.DoesNotExist:
        return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = ConversationSerializer(conversation)
    return Response(serializer.data)

@swagger_auto_schema(
    method='post',
    responses={
        201: openapi.Response(
            description="New conversation created",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'conversation_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        ),
        401: "Unauthorized"
    },
    operation_description="Create a new empty conversation"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_conversation(request):
    """Create a new empty conversation"""
    conversation = Conversation.objects.create(user=request.user)
    return Response({"conversation_id": conversation.id}, status=status.HTTP_201_CREATED)