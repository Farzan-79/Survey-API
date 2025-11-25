from django.urls import path
from .views import (
    SurveyListView
)

app_name= 'survey'
urlpatterns = [
    path("", SurveyListView.as_view())
]