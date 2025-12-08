from django.shortcuts import render
from rest_framework import generics, mixins, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .permissions import IsOwnerOrReadOnlyPermission
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import *
from .serializers import SurveyCreateSerializer, SurveyListSerializer, SurveyDetailSerializer, AnswerSerializer
# Create your views here.

class SurveyListCreateView(generics.ListCreateAPIView):
    queryset = Survey.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    http_method_names = ["get", "post", "options", 'head']
    
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
    http_method_names = ["get", "put", "options", "delete", 'head']

class ResponseDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        survey = get_object_or_404(Survey, slug=slug)
        serializer = SurveyDetailSerializer(survey, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request, slug):
        survey = get_object_or_404(Survey, slug=slug)

        payload = request.data.get('answers', None)
        if not payload:
            return Response({"detail": "Missing 'answers' list"}, status=400)
        with transaction.atomic():
            answers_created = []
            for answer in payload:
                serializer = AnswerSerializer(data=answer, context={'survey': survey, 'request': request, 'user':request.user})
                serializer.is_valid(raise_exception=True)
                answers_created.append(serializer.save())

        return Response({"answered": len(answers_created)})
        


