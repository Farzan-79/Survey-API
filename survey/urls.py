from django.urls import path
from .views import (
    SurveyListCreateView,
    SurveyDetailView,
    SubmissionView,
    ResultsView,
    SummarizeAnswers
)

app_name= 'survey'
urlpatterns = [
    path("", SurveyListCreateView.as_view(), name='list-create'),
    path("<slug:slug>/", SurveyDetailView.as_view(), name='detail'),
    path('<slug:slug>/response/', SubmissionView.as_view(), name='response'),
    path('<slug:slug>/results/', ResultsView.as_view(), name='results'),
    path('questions/<int:id>/summarize/', SummarizeAnswers.as_view(), name='summary')
]