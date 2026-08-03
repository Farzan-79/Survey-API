from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, extend_schema_view
from .serializers import (
    UserRegisterSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
    LogOutSerializer,
    MessageResponseSerializer
)

User = get_user_model()

class UserRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegisterSerializer

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'options', 'head']

    def get_object(self):
        return self.request.user

@extend_schema_view(
    post= extend_schema(
        summary= "Change user password",
        description= "User has to be logged in, and enter old password correctly",
        request= PasswordChangeSerializer,
        responses= {200: MessageResponseSerializer}
    )
) 
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ['options', 'post', 'head']

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Password Changed Successfully'}, status=status.HTTP_200_OK)

@extend_schema_view(
    post=extend_schema(
        summary="Log out",
        description="Blacklists the provided refresh token.",
        request=LogOutSerializer,
        responses={205: None},
    ),
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_205_RESET_CONTENT)

