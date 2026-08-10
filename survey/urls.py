from django.urls import path
from .views import (
    SurveyListCreateView,
    SurveyDetailView,
    SubmissionView,
    ResultsView,
    SummarizeAnswersView,
    PublicListView,
)

app_name= 'survey'
urlpatterns = [
    path("public/list/", PublicListView.as_view(), name='public-list'),
    path("", SurveyListCreateView.as_view(), name='list-create'),
    path("<slug:slug>/", SurveyDetailView.as_view(), name='detail'),
    path('<slug:slug>/response/', SubmissionView.as_view(), name='response'),
    path('<slug:slug>/results/', ResultsView.as_view(), name='results'),
    path('questions/<int:id>/summarize/', SummarizeAnswersView.as_view(), name='summary'),
]