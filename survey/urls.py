from django.urls import path
from .views import (
    SurveyListCreateView,
    SurveyDetailView
)

app_name= 'survey'
urlpatterns = [
    path("", SurveyListCreateView.as_view(), name='list-create'),
    path("<slug:slug>/", SurveyDetailView.as_view(), name='detail')
]