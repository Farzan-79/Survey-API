from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView, TokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/survey/', include('survey.urls')),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('api/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify', TokenVerifyView.as_view(), name='token_verify')

]
