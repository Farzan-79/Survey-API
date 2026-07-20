import pytest
from survey.models import Survey, Question, Choice, Answer, Submission
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIClient
#* These fixtures are accessible by all the other tests.
#* because this file is in the main dir, all apps have access too, and we wont be copy pasting fixtures in each app
#*  pytest gets them and gives them to whichever test needs them.

@pytest.fixture(autouse=True) #* for faster user creation, with a weak password hashing
def fast_password_hasher(settings):
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

@pytest.fixture
def user_factory():
    User = get_user_model()

    def create_user(username, email=None):
        return User.objects.create_user(
            username=username,
            email= email or f'{username}@gmail.com',
            password='PassWord123')
    
    return create_user

@pytest.fixture
def api_rf(rf):
    def _make_request(method='get', user=None):
        request = getattr(rf, method.lower())('/fake-url/')
        request.user = user if user is not None else AnonymousUser()
        return request
    return _make_request

@pytest.fixture
def api_client():
    return APIClient()

