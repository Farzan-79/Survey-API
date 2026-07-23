import pytest
from rest_framework import status
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from django.contrib.auth import get_user_model as User

#! ================================================================
#!                    UserRegisterView
#! ================================================================

@pytest.mark.django_db
def test_register_view_allows_anonymous_registration(api_client):
    payload = {
        'username': 'newuser',
        'password': 'PassWord!!1234',
        'confirm_password': 'PassWord!!1234',
        'email': 'meow@gmail.com'
    }
    url = reverse('account:register')
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_register_view_excludes_passwords_in_response(api_client):
    payload = {
        'username': 'newuser',
        'password': 'PassWord!!1234',
        'confirm_password': 'PassWord!!1234',
        'email': 'meow@gmail.com',
    }
    url = reverse('account:register')
    response = api_client.post(url, payload, 'json')

    assert set(response.data.keys()) == {'username', 'first_name', 'last_name', 'email'}

@pytest.mark.django_db
def test_register_view_saves_first_and_last_name_if_provided(api_client):
    payload = {
        'username': 'newuser',
        'password': 'PassWord!!1234',
        'confirm_password': 'PassWord!!1234',
        'email': 'meow@gmail.com',
        'first_name': 'far',
        'last_name': 'zan'
    }
    url = reverse('account:register')
    response = api_client.post(url, payload, 'json')
    user = User().objects.first()

    assert user.first_name == 'far'
    assert user.last_name == 'zan'

@pytest.mark.django_db
def test_register_view_rejects_duplicate_username(api_client, user_factory):
    user = user_factory('user')
    payload = {
        'username': 'user',
        'password': 'PassWord!!1234',
        'confirm_password': 'PassWord!!1234',
        'email': 'meow@gmail.com',
    }
    url = reverse('account:register')
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['errors'][0]['code'] == 'unique'

@pytest.mark.django_db
def test_register_view_rejects_mismatched_password(api_client, user_factory):
    payload = {
        'username': 'user',
        'password': 'PassWord!!11234',
        'confirm_password': 'PassWord!!1234',
        'email': 'meow@gmail.com',
    }
    url = reverse('account:register')
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['errors'][0]['code'] == 'password_mismatch'

#! ================================================================
#!                    UserProfileView
#! ================================================================

@pytest.mark.django_db
def test_profile_view_denies_anonymous_get(api_client):
    url = reverse('account:profile')
    response = api_client.get(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_profile_view_denies_anonymous_patch(api_client):
    url = reverse('account:profile')
    response = api_client.patch(url, {'first_name': 'far'})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_profile_view_shows_authenticated_users_own_data(api_client, user_factory):
    url = reverse('account:profile')
    user = user_factory('meow')
    api_client.force_authenticate(user)

    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data['username'] == 'meow'
    assert response.data['id'] == user.id

@pytest.mark.django_db
def test_profile_view_patches_the_editable_fields(api_client, user_factory):
    url = reverse('account:profile')
    user = user_factory('meow')
    api_client.force_authenticate(user)
    payload = {
        'first_name': 'far',
        'username' : 'woof'
    }
    response = api_client.patch(url, payload, 'json')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['username'] == 'meow'
    assert response.data['first_name'] == 'far'
    assert response.data['last_name'] == ''


@pytest.mark.django_db
def test_profile_view_rejects_put(api_client, user_factory):
    user = user_factory('profileuser4')
    api_client.force_authenticate(user)

    url = reverse('account:profile')
    response = api_client.put(url, {'first_name': 'x'}, 'json')

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

#! ================================================================
#!                    ChangePasswordView
#! ================================================================

@pytest.mark.django_db
def test_change_password_view_changes_password(user_factory, api_client):
    user= user_factory('user')
    payload = {
        'old_password': 'PassWord123',
        'new_password': 'NewPassWWord123',
        'confirm_new_password': 'NewPassWWord123'
    }
    url = reverse('account:change-password')
    api_client.force_authenticate(user)
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_200_OK
    assert user.check_password('NewPassWWord123')

@pytest.mark.django_db
def test_change_password_view_denies_anonymous(api_client):
    payload = {
        'old_password': 'PassWord123',
        'new_password': 'NewPassWWord123',
        'confirm_new_password': 'NewPassWWord123'
    }
    url = reverse('account:change-password')
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_change_password_view_denies_wrong_old_password(user_factory, api_client):
    user= user_factory('user')
    payload = {
        'old_password': 'PpppppassWord123',
        'new_password': 'NewPassWWord123',
        'confirm_new_password': 'NewPassWWord123'
    }
    url = reverse('account:change-password')
    api_client.force_authenticate(user)
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['errors'][0]['code'] == 'invalid_old_password'
    assert user.check_password('PassWord123')

@pytest.mark.django_db
def test_change_password_view_denies_mismatched_new_password(user_factory, api_client):
    user= user_factory('user')
    payload = {
        'old_password': 'PassWord123',
        'new_password': 'NewPassWWord123',
        'confirm_new_password': 'NewNewPassWWord123'
    }
    url = reverse('account:change-password')
    api_client.force_authenticate(user)
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['errors'][0]['code'] == 'password_mismatch'
    assert user.check_password('PassWord123')

#! ================================================================
#!                       LogoutView
#! ================================================================

@pytest.mark.django_db
def test_logout_view_denies_anonymous(api_client, user_factory):
    url = reverse('account:logout')
    user = user_factory('user')
    token = RefreshToken.for_user(user)
    #* no authentication
    response = api_client.post(url, {'refresh': str(token)}, 'json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_logout_view_rejects_get(api_client, user_factory):
    user = user_factory('user')
    url = reverse('account:logout')
    api_client.force_authenticate(user)
    response = api_client.get(url)

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

@pytest.mark.django_db
def test_logout_view_blacklists_refresh_token(api_client, user_factory):
    user = user_factory('user')
    token = RefreshToken.for_user(user)
    url = reverse('account:logout')
    api_client.force_authenticate(user)
    response = api_client.post(url, {'refresh': str(token)}, 'json')

    assert response.status_code == status.HTTP_205_RESET_CONTENT
    assert BlacklistedToken.objects.filter(token__jti=token['jti']).exists()

@pytest.mark.django_db
def test_logout_view_rejects_invalid_token(api_client, user_factory):
    user = user_factory('user')
    url = reverse('account:logout')
    api_client.force_authenticate(user)
    response = api_client.post(url, {'refresh': 'not_a_valid_token'}, 'json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_logout_view_rejects_blacklisted_refresh_token(api_client, user_factory):
    user = user_factory('user')
    token = RefreshToken.for_user(user)
    url = reverse('account:logout')
    api_client.force_authenticate(user)
    response = api_client.post(url, {'refresh': str(token)}, 'json')
    response_repeat = api_client.post(url, {'refresh': str(token)}, 'json')

    assert response_repeat.status_code == status.HTTP_400_BAD_REQUEST

#! ================================================================
#!         Token obtain / refresh (library integration)
#! ================================================================
#* These test simplejwt's own views, not my own code - but they're the
#* only way to prove your logout's blacklist actually blocks the HTTP
#* refresh flow, not just the DB row. Kept minimal on purpose.

@pytest.mark.django_db
def test_token_obtain_view_returns_tokens_for_valid_credentials(api_client, user_factory):
    user_factory('loginuser')  # password='PassWord123'
    url = reverse('account:token_obtain')
    response = api_client.post(url, {'username': 'loginuser', 'password': 'PassWord123'}, 'json')

    assert response.status_code == status.HTTP_200_OK
    assert 'access' in response.data
    assert 'refresh' in response.data

@pytest.mark.django_db
def test_token_obtain_view_rejects_invalid_credentials(api_client, user_factory):
    user_factory('loginuser')  # password='PassWord123'
    url = reverse('account:token_obtain')
    response = api_client.post(url, {'username': 'loginuser', 'password': 'meowmeow'}, 'json')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_token_refresh_returns_new_acess_token_and_rotates_refresh_token(api_client, user_factory):
    user = user_factory('loginuser')  
    url = reverse('account:token_obtain')
    response = api_client.post(url, {'username': 'loginuser', 'password': 'PassWord123'}, 'json')
    access = response.data['access']
    refresh = response.data['refresh']

    api_client.force_authenticate(user)
    url_refresh = reverse('account:token_refresh')
    response_refresh = api_client.post(url_refresh, {'refresh': refresh}, 'json')
    
    assert response_refresh.status_code == status.HTTP_200_OK
    assert 'access' in response_refresh.data
    assert 'refresh' in response_refresh.data
    assert response_refresh.data['access'] != access
    assert response_refresh.data['refresh'] != refresh

    new_refresh = api_client.post(url_refresh, {'refresh': refresh}, 'json')
    assert new_refresh.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_logout_then_refresh_is_rejected(api_client, user_factory):
    user = user_factory('fulluser')
    token = RefreshToken.for_user(user)
    api_client.force_authenticate(user)

    logout_url = reverse('account:logout')
    logout_response = api_client.post(logout_url, {'refresh': str(token)}, 'json')
    assert logout_response.status_code == status.HTTP_205_RESET_CONTENT
    
    refresh_url = reverse('account:token_refresh')
    refresh_response = api_client.post(refresh_url, {'refresh': str(token)}, 'json')

    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED



