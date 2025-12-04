from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only= True)

    class Meta:
        model = User
        fields = [
            'username',
            'password'
        ]

    def create(self, validated_data):
        return User.objects.create_user(
            username = validated_data['username'],
            password = validated_data['password']
        )