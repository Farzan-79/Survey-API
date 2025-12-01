from django.shortcuts import render
from rest_framework import generics, mixins, permissions
from .permissions import IsOwnerOrReadOnlyPermission

from .models import *
from .serializers import SurveyCreateSerializer, SurveyListSerializer, SurveyDetailSerializer
# Create your views here.

class SurveyListCreateView(generics.ListCreateAPIView):
    queryset = Survey.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.request.method == "POST":
            return SurveyCreateSerializer
        else:
            return SurveyListSerializer
        
    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)
        
        
        

class SurveyDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Survey.objects.all()
    lookup_field = 'slug'
    serializer_class = SurveyDetailSerializer
    permission_classes = [IsOwnerOrReadOnlyPermission]

    def get_serializer_context(self):
        context = super().get_serializer_context()

        # Add the survey instance globally
        if self.kwargs.get('slug'):
            survey = self.get_object()
            context['survey'] = survey
        return context


