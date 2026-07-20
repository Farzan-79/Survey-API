import pytest
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model

@pytest.mark.django_db
def test_user_str_returns_username(user_factory):
    user = user_factory('meow')
    assert str(user) == 'meow'
    assert user.email == 'meow@gmail.com'

@pytest.mark.django_db
def test_user_with_duplicate_email_raises_integrity_error(user_factory):
    user1 = user_factory('user 1', email='meow@gamil.com')
    with pytest.raises(IntegrityError):
        user2 = user_factory('user 2', email='meow@gamil.com')

@pytest.mark.django_db
def test_user_with_duplicate_username_raises_integrity_error(user_factory):
    user1 = user_factory('user', email='meow@gamil.com')
    with pytest.raises(IntegrityError):
        user2 = user_factory('user', email='meowww@gamil.com')


