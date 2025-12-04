from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView, TokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/survey/', include('survey.urls')),
    path('api/auth/', include('account.urls'))
]
