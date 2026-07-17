import pytest
from survey.models import Survey, Question, Choice, Answer, Submission
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
#* These fixtures are accessible by all the other tests. pytest gets them and gives them to whichever test needs them.

@pytest.fixture(autouse=True) #* for faster user creation, with a weak password hashing
def fast_password_hasher(settings):
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


#! ----------------------- MODELS ----------------------------

@pytest.fixture
def user_factory():
    User = get_user_model()

    def create_user(username):
        return User.objects.create_user(username=username, password='PassWord123')
    
    return create_user

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
        required= True
    )

@pytest.fixture
def choices(question):
    for n in range(4):
        Choice.objects.create(title=f'Choice {n}', question=question)
    return question.choices.all()

@pytest.fixture
def submission(survey):
    return Submission.objects.create(survey=survey)

@pytest.fixture
def answer(question, submission, choices):
    return Answer.objects.create(question=question, submission=submission, chosen_choice=choices.last())
    

#! ----------------------- REQUEST --------------------------

@pytest.fixture
def api_rf(rf):
    def _make_request(method='get', user=None):
        request = getattr(rf, method.lower())('/fake-url/')
        request.user = user if user is not None else AnonymousUser()
        return request
    return _make_request

#! ----------------------- SERIALIZERS -----------------------

@pytest.fixture
def full_survey(survey):
    q1 = Question.objects.create(survey=survey, title='q1', question_type='multiple_choice', required=True)
    Choice.objects.create(question=q1, title='c1')
    Choice.objects.create(question=q1, title='c2')
    Question.objects.create(survey=survey, title='q2', question_type='free_text', required=False)
    return survey

