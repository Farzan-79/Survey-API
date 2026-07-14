from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    Username = serializers.CharField(source='username')
    Email = serializers.EmailField(source='email', required=False)
    Password = serializers.CharField(source='password', write_only= True)

    class Meta:
        model = User
        fields = [
            'Username',
            'Email',
            'Password',
        ]

    def validate_Username(self, value):
        if len(value) < 3:
            raise serializers.ValidationError({"Username:" "Usernames should have at least 3 characters"},
                                              code= "username_too_short")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError({"Username": "This Username is Taken"},
                                              code= "duplicate_username")
        return value
    
    def validate_Email(self, value):
        validate_email(value)
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError({"Email": "This Email is Taken"},
                                              code= "duplicate_email")
        return value
    
    def validate_Password(self, value):
        validate_password(value)
        return value


    def create(self, validated_data):
        return User.objects.create_user(**validated_data)