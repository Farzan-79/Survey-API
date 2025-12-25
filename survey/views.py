from django.shortcuts import render
from rest_framework import generics, mixins, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .permissions import IsOwnerOrReadOnlyPermission, IsOwnerOrSuperuser
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Prefetch, Count

from .models import *
from .serializers import (
    SurveyCreateSerializer,
    SurveyListSerializer,
    SurveyDetailSerializer,
    SurveyDetailReadSerializer,
    SurveyDetailWriteSerializer,
    SurveyUpdateMessageSerializer,
    SurveyCreatedMessageSerializer,
    SubmissionSerializer,
    SurveyResaultSerializer)
# Create your views here.
# i will send you my views and serializers final versions. first, i need you to tell me why did i use a different approach for each view. i mean what is the reason it would be better for something like resaults view to be APIView and i handle all those quesrysets and for others like the detail view


class SurveyListCreateView(generics.ListCreateAPIView):
    queryset = Survey.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "options", 'head']
    
    def get_serializer_class(self):
        if self.request.method == "POST":
            return SurveyCreateSerializer
        else:
            return SurveyListSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        survey = serializer.save(user=request.user)

        question_count = len(serializer.validated_data.get('questions'))
        response_serializer = SurveyCreatedMessageSerializer(survey, context={'question_count': question_count, 'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None
        if user and user.is_superuser:
            return Survey.objects.select_related('user') \
                .annotate(question_count=Count('questions', distinct=True)) \
                .annotate(submission_count=Count('submissions', distinct=True))
        elif user:
            return Survey.objects.filter(user=user).select_related('user') \
                .annotate(question_count=Count('questions', distinct=True)) \
                .annotate(submission_count=Count('submissions', distinct=True))
        else:
            return Survey.objects.none()
        
class SurveyDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Survey.objects.prefetch_related(Prefetch('questions',
                                                        queryset=Question.objects.prefetch_related('choices'),
                                                        to_attr='prefetched_questions')) \
        .annotate(submission_count=Count('submissions', distinct=True)) \
        .select_related('user')
    lookup_field = 'slug'
    permission_classes = [IsOwnerOrSuperuser]
    http_method_names = ["get", "put", "options", "delete", 'head']

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method == 'PUT':
            return SurveyDetailWriteSerializer
        return SurveyDetailReadSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        survey = serializer.save()

        if getattr(instance, '_prefetched_objects_cache', None):
            #* If 'prefetch_related' has been applied to a queryset, we need to
            #* forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        question_count = len(serializer.validated_data.get('questions')) if serializer.validated_data.get('questions') else survey.questions.count()
        if serializer._frozen:
            response_serializer = SurveyUpdateMessageSerializer(survey, context={'request': request,
                                                                             'question_count': question_count,
                                                                             'frozen': True})
        else:
            response_serializer = SurveyUpdateMessageSerializer(survey, context={'request': request,
                                                                             'question_count': question_count})
        return Response(response_serializer.data, status= status.HTTP_200_OK)

class SubmissionView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        survey = get_object_or_404(Survey.objects \
                                   .prefetch_related('questions__choices') \
                                   .annotate(submission_count=Count('submissions'))
                                   ,slug=slug)
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
        survey = get_object_or_404( Survey.objects \
            .prefetch_related(Prefetch('questions', queryset=question_qs, to_attr='prefetched_questions')) \
            .annotate(times_submitted = Count('submissions')) \
            , slug=slug \
        )
        self.check_object_permissions(request, survey)
        serializer = SurveyResaultSerializer(survey, context={'request': request})
        return Response(serializer.data)

        
    



