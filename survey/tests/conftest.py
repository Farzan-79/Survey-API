import pytest
from survey.models import Survey, Question, Choice, Answer, Submission
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIClient
#* These fixtures are accessible by all the other tests. pytest gets them and gives them to whichever test needs them.

@pytest.fixture
def survey(db):
    return Survey.objects.create(title='Base Survey')

@pytest.fixture
def question(survey):
    return Question.objects.create(
        survey = survey,
        title = 'Pick One',
        question_type = 'multiple_choice'
    )

@pytest.fixture
def ft_question(survey):
    return Question.objects.create(
        survey= survey,
        title= 'Explain yourself',
        question_type= 'free_text',
        required= False
    )

@pytest.fixture
def choices(question):
    for n in range(1,5):
        Choice.objects.create(title=f'Choice {n}', question=question)
    return question.choices.all()

@pytest.fixture
def submission(survey):
    return Submission.objects.create(survey=survey)

@pytest.fixture
def answer(question, submission, choices):
    return Answer.objects.create(question=question, submission=submission, chosen_choice=choices.last())

@pytest.fixture
def full_survey(survey):
    q1 = Question.objects.create(survey=survey, title='q1', question_type='multiple_choice', required=True)
    Choice.objects.create(question=q1, title='c1')
    Choice.objects.create(question=q1, title='c2')
    Question.objects.create(survey=survey, title='q2', question_type='free_text', required=False)
    return survey

