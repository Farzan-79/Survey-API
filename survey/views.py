from django.shortcuts import render
from rest_framework import generics, mixins, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .permissions import IsOwnerOrReadOnlyPermission, IsOwnerOrSuperuser
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Prefetch, Count

from .models import *
from .serializers import SurveyCreateSerializer, SurveyListSerializer, SurveyDetailSerializer, AnswerSerializer, SubmissionSerializer, SurveyResaultSerializer
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

    # def get_queryset(self):
    #     user = self.request.user if self.request.user.is_authenticated else None
    #     if user.is_superuser:
    #         return Survey.objects.all()
    #     elif user:
    #         return Survey.objects.filter(user=user)
        
class SurveyDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Survey.objects.all()
    lookup_field = 'slug'
    serializer_class = SurveyDetailSerializer
    permission_classes = [IsOwnerOrSuperuser]
    http_method_names = ["get", "put", "options", "delete", 'head']

class SubmissionView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        survey = get_object_or_404(Survey, slug=slug)
        serializer = SurveyDetailSerializer(survey, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request, slug):
        payload = request.data
        survey = get_object_or_404(Survey, slug=slug)
        serializer = SubmissionSerializer(data=payload, context={'survey': survey, 'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class ResaultsView(APIView):
    permission_classes = [IsOwnerOrSuperuser]
    def get(self, request, slug):
        text_answer_qs = Answer.objects.filter(text_answer__isnull=False).only('text_answer', 'question_id')
        choice_qs = Choice.objects.annotate(times_selected=Count('answers')).order_by('id')
        question_qs = Question.objects.filter(survey__slug=slug) \
            .prefetch_related(Prefetch('choices', queryset=choice_qs, to_attr='prefetched_choices'),
                              Prefetch('answers',text_answer_qs ,to_attr='prefetched_text_answers' )) \
            .annotate(times_answered = Count('answers')) \
            .order_by('id')
        survey = Survey.objects \
            .prefetch_related(Prefetch('questions', queryset=question_qs, to_attr='prefetched_questions')) \
            .annotate(times_submitted = Count('submissions')) \
            .get(slug=slug) \
        
        serializer = SurveyResaultSerializer(survey, context={'request': request})
        return Response(serializer.data)

        
    



