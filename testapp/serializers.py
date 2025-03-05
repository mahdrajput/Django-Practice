from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
import re

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')

class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2')
        extra_kwargs = {
            'password': {'write_only': True, 'style': {'input_type': 'password'}},
        }
    
    def validate_password(self, value):
        """
        Validate password meets security requirements:
        - At least 8 characters long
        - Contains uppercase letter
        - Contains a number
        - Contains a special character
        """
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
            
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password must contain at least one number.")
            
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must contain at least one special character.")
            
        return value
    
    def validate(self, data):
        # Check that passwords match
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password2": "Passwords don't match"})
        return data
    
    def create(self, validated_data):
        # Remove password2 as it's not needed for user creation
        validated_data.pop('password2', None)
        
        # Check if username already exists
        if User.objects.filter(username=validated_data['username']).exists():
            raise serializers.ValidationError({'username': 'This username is already taken'})
            
        # Check if email already exists
        if User.objects.filter(email=validated_data['email']).exists():
            raise serializers.ValidationError({'email': 'This email is already registered'})
        
        # Create user with validated data
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'}, trim_whitespace=False)
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if username and password:
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials. Please try again.')
        else:
            raise serializers.ValidationError('Must include "username" and "password".')
            
        data['user'] = user
        return data

class ProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    current_password = serializers.CharField(
        write_only=True, 
        required=False,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True, 
        required=False,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 
                  'current_password', 'new_password')
        read_only_fields = ('username',)  # Username cannot be changed
        
    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value
        
    def validate(self, data):
        # If changing password, validate current password
        if 'new_password' in data and data['new_password']:
            if 'current_password' not in data or not data['current_password']:
                raise serializers.ValidationError(
                    {"current_password": "Current password is required to set a new password"}
                )
                
            # Check if current password is correct
            if not self.context['request'].user.check_password(data['current_password']):
                raise serializers.ValidationError(
                    {"current_password": "Current password is incorrect"}
                )
                
            # Validate new password strength
            if 'new_password' in data:
                password = data['new_password']
                if len(password) < 8:
                    raise serializers.ValidationError(
                        {"new_password": "Password must be at least 8 characters long."}
                    )
                
                if not re.search(r'[A-Z]', password):
                    raise serializers.ValidationError(
                        {"new_password": "Password must contain at least one uppercase letter."}
                    )
                    
                if not re.search(r'[0-9]', password):
                    raise serializers.ValidationError(
                        {"new_password": "Password must contain at least one number."}
                    )
                    
                if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                    raise serializers.ValidationError(
                        {"new_password": "Password must contain at least one special character."}
                    )
        
        return data
    
    def update(self, instance, validated_data):
        # Remove password fields from data used to update the model
        new_password = validated_data.pop('new_password', None)
        validated_data.pop('current_password', None)  # Remove current_password
        
        # Handle password change if requested
        if new_password:
            instance.set_password(new_password)
        
        # Update user fields
        for field, value in validated_data.items():
            setattr(instance, field, value)
                
        instance.save()
        return instance