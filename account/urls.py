from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView, TokenObtainPairView
from .views import UserRegisterView


urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify')
]