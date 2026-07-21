import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from account.serializers import (
    UserRegisterSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
    LogOutSerializer,
)

User = get_user_model()

#! ================================================================
#!                   UserRegisterSerializer
#! ================================================================

@pytest.mark.django_db
def test_user_register_creates_user_with_valid_data():
    payload = {
        'username': 'fkn',
        'password': 'Fkn0217184',
        'confirm_password': 'Fkn0217184',
        'email': 'email@example.com'
    }
    serializer = UserRegisterSerializer(data=payload)
    assert serializer.is_valid()

    user = serializer.save()

    assert user.username == 'fkn'
    assert user.email == 'email@example.com'
    assert user.check_password('Fkn0217184') == True
    assert user.password != 'Fkn0217184'

@pytest.mark.django_db
def test_user_register_rejects_short_username():
    payload = {
        'username': 'fk',
        'password': 'Fkn0217184',
        'confirm_password': 'Fkn0217184',
        'email': 'email@example.com'
    }
    serializer = UserRegisterSerializer(data=payload)
    assert serializer.is_valid() is False
    assert serializer.errors['username'][0].code == 'username_too_short'

@pytest.mark.django_db
def test_user_register_rejects_duplicate_username(user_factory):
    user1 = user_factory('fkn')

    payload = {
        'username': 'fkn',
        'password': 'Fkn0217184',
        'confirm_password': 'Fkn0217184',
        'email': 'email@example.com'
    }

    serializer = UserRegisterSerializer(data=payload)

    assert serializer.is_valid() is False
    assert serializer.errors['username'][0].code == 'unique' 

@pytest.mark.django_db
def test_user_register_rejects_duplicate_email(user_factory):
    user1 = user_factory('user', email='email@example.com')

    payload = {
        'username': 'fkn',
        'password': 'Fkn0217184',
        'confirm_password': 'Fkn0217184',
        'email': 'email@example.com'
    }

    serializer = UserRegisterSerializer(data=payload)

    assert serializer.is_valid() is False
    assert serializer.errors['email'][0].code == 'unique' 

@pytest.mark.django_db
def test_user_register_rejects_invalid_email():
    payload = {
        'username': 'fkn',
        'password': 'Fkn0217184',
        'confirm_password': 'Fkn0217184',
        'email': 'emailexample.com'
    }

    serializer = UserRegisterSerializer(data=payload)

    assert serializer.is_valid() is False
    assert serializer.errors['email'][0].code == 'invalid' 

@pytest.mark.django_db
def test_user_register_rejects_password_mismatch():
    payload = {
        'username': 'fkn',
        'password': 'Fkn0217184',
        'confirm_password': 'Fffkn0217184',
        'email': 'email@example.com'
    }

    serializer = UserRegisterSerializer(data=payload)

    assert serializer.is_valid() is False
    assert serializer.errors['confirm_password'][0].code == 'password_mismatch' 

@pytest.mark.django_db
def test_user_register_enforces_password_strenght():
    payload = {
        'username': 'fkn',
        'password': '1234567890',
        'confirm_password': '1234567890',
        'email': 'email@example.com'
    }

    serializer = UserRegisterSerializer(data=payload)

    assert serializer.is_valid() is False
    assert 'password' in serializer.errors.keys()

@pytest.mark.django_db
def test_user_register_requires_all_fields():
    payload = {}
    serializer = UserRegisterSerializer(data=payload)

    assert serializer.is_valid() is False
    assert set(serializer.errors.keys()) == {'username', 'password', 'email', 'confirm_password'}
    for err in serializer.errors.values():
        assert err[0].code == 'required'

#! ================================================================
#!                   UserProfileSerializer
#! ================================================================

@pytest.mark.django_db
def test_user_profile_exposes_expected_fields(user_factory):
    user = user_factory('meow')
    data = UserProfileSerializer(user).data

    assert set(data.keys()) == {'id', 'username', 'email', 'first_name', 'last_name', 'date_joined'}

@pytest.mark.django_db
def test_user_profile_changes_only_the_writable_fields(user_factory):
    user = user_factory('meow')
    payload = {
        'id': 4, # should not change
        'username': 'meow2', # should not change
        'email': 'moewmoewmoew@gamil.com', # should not change
        'first_name': 'me', # should change
        'last_name': 'ow' # should change
    }
    serializer = UserProfileSerializer(user ,data=payload, partial=True)

    assert serializer.is_valid()
    user = serializer.save()
    assert user.id == 1
    assert user.username == 'meow'
    assert user.email == 'meow@gmail.com'
    assert user.first_name == 'me'
    assert user.last_name == 'ow'

#! ================================================================
#!                   PasswordChangeSerializer
#! ================================================================

@pytest.mark.django_db
def test_password_change_serializer_changes_password_when_valid(api_rf, user_factory):
    user = user_factory('user')
    request = api_rf('post', user=user)
    payload = {
        'old_password': 'PassWord123',
        'new_password': 'STrong!!Pass',
        'confirm_new_password': 'STrong!!Pass'
    }
    serializer = PasswordChangeSerializer(data=payload, context={'request': request})
    
    assert serializer.is_valid(), serializer.errors
    user = serializer.save()
    assert user.check_password('STrong!!Pass')

@pytest.mark.django_db
def test_password_change_serializer_enforces_strong_password(api_rf, user_factory):
    user = user_factory('user')
    request = api_rf('post', user=user)
    payload = {
        'old_password': 'PassWord123',
        'new_password': 'pass1234',
        'confirm_new_password': 'pass1234'
    }
    serializer = PasswordChangeSerializer(data=payload, context={'request': request})
    
    assert serializer.is_valid() is False
    assert 'new_password' in serializer.errors

@pytest.mark.django_db
def test_password_change_serializer_rejects_new_password_mismatch(api_rf, user_factory):
    user = user_factory('user')
    request = api_rf('post', user=user)
    payload = {
        'old_password': 'PassWord123',
        'new_password': 'Strong!!Pass',
        'confirm_new_password': 'Strong!!Passs'
    }
    serializer = PasswordChangeSerializer(data=payload, context={'request': request})
    
    assert serializer.is_valid() is False
    assert serializer.errors['confirm_new_password'][0].code == 'password_mismatch'

@pytest.mark.django_db
def test_password_change_serializer_rejects_wrong_old_password(api_rf, user_factory):
    user = user_factory('user')
    request = api_rf('post', user=user)
    payload = {
        'old_password': 'PassWord1234',
        'new_password': 'pass1234',
        'confirm_new_password': 'pass1234'
    }
    serializer = PasswordChangeSerializer(data=payload, context={'request': request})
    
    assert serializer.is_valid() is False
    assert serializer.errors['old_password'][0].code == 'invalid_old_password'

@pytest.mark.django_db
def test_password_change_serializer_requires_all_fields(api_rf, user_factory):
    user = user_factory('user')
    request = api_rf('post', user=user)
    payload = {}
    serializer = PasswordChangeSerializer(data=payload, context={'request': request})

    assert serializer.is_valid() is False
    assert set(serializer.errors.keys()) == {'old_password', 'confirm_new_password', 'new_password'}
    for err in serializer.errors.values():
        assert err[0].code == 'required'

#! ================================================================
#!                       LogOutSerializer
#! ================================================================

@pytest.mark.django_db
def test_logout_serializer_blacklists_valid_refresh_token(user_factory):
    user = user_factory('user')
    token = RefreshToken.for_user(user)

    serializer = LogOutSerializer(data= {'refresh': str(token)})
    assert serializer.is_valid(), serializer.errors
    serializer.save()

    #* each token has a unique jti (JWT ID) as identifier
    assert BlacklistedToken.objects.filter(token__jti= token['jti']).exists()

@pytest.mark.django_db
def test_logout_serializer_rejects_wrong_refresh_token():
    serializer = LogOutSerializer(data={'refresh': 'some_garbage_token'})
    assert serializer.is_valid() is False
    assert serializer.errors['refresh'][0].code == 'invalid_refresh_token'

@pytest.mark.django_db
def test_logout_serializer_rejects_already_blacklisted_token(user_factory):
    user = user_factory('user')
    token = RefreshToken.for_user(user)

    first_logout = LogOutSerializer(data={'refresh': str(token)})
    assert first_logout.is_valid(), first_logout.errors
    first_logout.save()

    second_logout = LogOutSerializer(data={'refresh': str(token)})
    assert second_logout.is_valid() is False
    assert second_logout.errors['refresh'][0].code == 'invalid_refresh_token'

@pytest.mark.django_db
def test_logout_serializer_rejects_access_token_as_refresh_token(user_factory):
    user = user_factory('user')
    token = AccessToken.for_user(user)

    serializer = LogOutSerializer(data= {'refresh': str(token)})
    assert serializer.is_valid() is False
    assert serializer.errors['refresh'][0].code == 'invalid_refresh_token'

@pytest.mark.django_db
def test_logout_serializer_requires_refresh_field():
    serializer = LogOutSerializer(data={})
    assert serializer.is_valid() is False
    assert serializer.errors['refresh'][0].code == 'required'
