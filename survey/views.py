from django.shortcuts import render
from rest_framework import generics, mixins

from .models import *
from .serializers import SurveySerializer, QuestionSerializer
# Create your views here.

class SurveyListView(generics.ListCreateAPIView):
    queryset = Survey.objects.all()
    serializer_class = SurveySerializer


