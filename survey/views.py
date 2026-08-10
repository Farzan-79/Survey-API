from django.shortcuts import render
from rest_framework import generics, mixins, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from survey.permissions import IsOwnerOrSuperuser
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Prefetch, Count
from drf_spectacular.utils import extend_schema, extend_schema_view

from survey.services.summary import summarize_answers
from survey.services.exceptions import AIServiceUnavailable

from .models import (
    Survey,
    Question,
    Choice,
    Answer,
)
from .serializers import (
    SurveyCreateSerializer,
    SurveyListSerializer,
    SurveyDetailSerializer,
    SurveyDetailReadSerializer,
    SurveyDetailWriteSerializer,
    SurveyUpdateMessageSerializer,
    SurveyCreatedMessageSerializer,
    SubmissionSerializer,
    SurveyResultSerializer,
    SummaryResponseSerializer,
    ErrorResponseSerializer,)


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
        serializer = self.get_serializer(data=request.data, context={'user': request.user})
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
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        survey = serializer.save()

        question_count = len(serializer.validated_data.get('questions')) if serializer.validated_data.get('questions') else survey.questions.count()
        if serializer._frozen:
            response_serializer = SurveyUpdateMessageSerializer(survey, context={'request': request,
                                                                             'question_count': question_count,
                                                                             'frozen': True})
        else:
            response_serializer = SurveyUpdateMessageSerializer(survey, context={'request': request,
                                                                             'question_count': question_count})
        return Response(response_serializer.data, status= status.HTTP_200_OK)

@extend_schema_view(
    get= extend_schema(
        summary = "Get survey form for responding",
        description = "Public endpoint. Returns the survey's questions so a client can render a submission form.",
        responses = SurveyDetailSerializer
    ),
    post= extend_schema(
        summary = "Submit a response to a survey",
        description = "Public endpoint. Accepts answers for each question and creates a Submission.",
        request= SubmissionSerializer,
        responses= {201: SubmissionSerializer}
    )
)
class SubmissionView(APIView):

    def get_permissions(self):
        slug = self.kwargs['slug']
        survey = get_object_or_404(Survey, slug=slug)
        if not survey.is_public:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

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
        if not survey.is_active:
            return Response(
                {"detail": "This survey is closed and no longer accepting responses."},
                status=status.HTTP_400_BAD_REQUEST,
        )
        serializer = SubmissionSerializer(data=payload, context={'survey': survey, 'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@extend_schema_view(
    get=extend_schema(
        summary="Get aggregated survey results",
        description="Owner/superuser only. Returns per-question answer counts and percentages.",
        responses=SurveyResultSerializer,
    ),
)
class ResultsView(APIView):
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
        serializer = SurveyResultSerializer(survey, context={'request': request})
        return Response(serializer.data)

@extend_schema_view(
    post=extend_schema(
        summary="Summerizes text answers for given question",
        description="the question must be a free text with submitted answers, and only the owner can send the request",
        responses={
            200: SummaryResponseSerializer,
            400: ErrorResponseSerializer,
            503: ErrorResponseSerializer,
        }
    )
)
class SummarizeAnswersView(APIView):
    permission_classes = [IsOwnerOrSuperuser]
    def post(self, request, id):
        question = get_object_or_404(Question, id=id)
        self.check_object_permissions(request, question.survey)

        if question.question_type != "free_text":
            return Response({"detail": "Question is not Free Text"}, status=status.HTTP_400_BAD_REQUEST)
        
        question_title = question.title
        answers = list(question.answers.values_list('text_answer', flat=True))
        clean_answers = [a.strip() for a in answers if a.strip()]
        if not clean_answers:
            return Response(
                {"summary": "There are no answers to summarize."},
                status=status.HTTP_200_OK)
        
        try:
            response = summarize_answers(question_title, clean_answers)
        except AIServiceUnavailable:
            return Response(
                {"detail": (
                "AI service is currently unavailable. "
                "Please try again later."
            )},
            status= status.HTTP_503_SERVICE_UNAVAILABLE
            )


        return Response({"summary":response}, status=status.HTTP_200_OK)

class PublicListView(generics.ListAPIView):
    queryset = (
        Survey.objects
        .filter(
            is_public=True,
            is_active=True,
        )
        .select_related("user")
        .annotate(
            question_count=Count("questions", distinct=True),
            submission_count=Count("submissions", distinct=True),
        )
        .order_by("-created")[:6]
    )

    serializer_class = SurveyListSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={'pub': True, 'request': request, 'view':self})
        return Response(serializer.data, status=status.HTTP_200_OK)