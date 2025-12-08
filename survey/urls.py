from django.urls import path
from .views import (
    SurveyListCreateView,
    SurveyDetailView,
    ResponseDetailView,
)

app_name= 'survey'
urlpatterns = [
    path("", SurveyListCreateView.as_view(), name='list-create'),
    path("<slug:slug>/", SurveyDetailView.as_view(), name='detail'),
    path('<slug:slug>/response/', ResponseDetailView.as_view(), name='response')
]