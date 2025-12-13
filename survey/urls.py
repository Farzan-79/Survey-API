from django.urls import path
from .views import (
    SurveyListCreateView,
    SurveyDetailView,
    SubmissionView,
    ResaultsView
)

app_name= 'survey'
urlpatterns = [
    path("", SurveyListCreateView.as_view(), name='list-create'),
    path("<slug:slug>/", SurveyDetailView.as_view(), name='detail'),
    path('<slug:slug>/response/', SubmissionView.as_view(), name='response'),
    path('<slug:slug>/resaults/', ResaultsView.as_view(), name='resaults')
]