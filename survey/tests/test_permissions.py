import pytest
from survey.permissions import IsOwnerOrReadOnlyPermission, IsOwnerOrSuperuser
from survey.models import Survey

@pytest.mark.django_db
def test_readonly_perm_allows_safe_methods_for_any_authenticated_user(user_factory, api_rf):
    owner = user_factory('owner')
    stranger = user_factory('stranger')
    survey = Survey.objects.create(title='survey', user=owner)

    request = api_rf(method='get', user=stranger)
    permission = IsOwnerOrReadOnlyPermission()

    assert permission.has_object_permission(request, None, survey) is True

@pytest.mark.django_db
def test_readonly_perm_allows_safe_methods_for_anonymous_user(user_factory, api_rf):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)

    request = api_rf(method='get', user=None)
    permission = IsOwnerOrReadOnlyPermission()

    assert permission.has_object_permission(request, None, survey) is True

@pytest.mark.django_db
def test_readonly_perm_allows_unsafe_methods_for_owner(user_factory, api_rf):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)

    request = api_rf(method='put', user=owner)
    permission = IsOwnerOrReadOnlyPermission()

    assert permission.has_object_permission(request, None, survey) is True

@pytest.mark.django_db
def test_readonly_perm_denies_unsafe_methods_for_non_owner(user_factory, api_rf):
    owner = user_factory('owner')
    stranger = user_factory('stranger')
    survey = Survey.objects.create(title='survey', user=owner)

    request = api_rf(method='put', user=stranger)
    permission = IsOwnerOrReadOnlyPermission()

    assert permission.has_object_permission(request, None, survey) is False

@pytest.mark.django_db
def test_readonly_perm_allows_unsafe_methods_for_superuser(user_factory, api_rf):
    owner = user_factory('owner')
    admin = user_factory('admin')
    admin.is_superuser = True
    admin.save()
    survey = Survey.objects.create(title='survey', user=owner)

    request = api_rf(method='delete', user=admin)
    permission = IsOwnerOrReadOnlyPermission()

    assert permission.has_object_permission(request, None, survey) is True

@pytest.mark.django_db
def test_readonly_perm_denies_unsafe_methods_when_owner_does_not_exist(user_factory, api_rf, survey):
    stranger = user_factory('stranger')
    request = api_rf('delete', stranger)
    permission = IsOwnerOrReadOnlyPermission()

    assert permission.has_object_permission(request, None, survey) is False

@pytest.mark.django_db
def test_isownerorsuperuser_denies_anonymous_user(user_factory, api_rf):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)
    
    request = api_rf('get', None)
    permission = IsOwnerOrSuperuser()

    assert permission.has_object_permission(request, None, survey) is False

@pytest.mark.django_db
def test_isownerorsuperuser_denies_non_owner_user(user_factory, api_rf):
    owner = user_factory('owner')
    stranger = user_factory('stranger')
    survey = Survey.objects.create(title='survey', user=owner)
    
    request = api_rf('get', stranger)
    permission = IsOwnerOrSuperuser()

    assert permission.has_object_permission(request, None, survey) is False

@pytest.mark.django_db
def test_isownerorsuperuser_allows_owner(user_factory, api_rf):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)
    
    request = api_rf('get', owner)
    permission = IsOwnerOrSuperuser()

    assert permission.has_object_permission(request, None, survey) is True

@pytest.mark.django_db
def test_isownerorsuperuser_allows_superuser(user_factory, api_rf):
    owner = user_factory('owner')
    admin = user_factory('admin')
    admin.is_superuser = True
    admin.save()
    survey = Survey.objects.create(title='survey', user=owner)
    
    request = api_rf('get', admin)
    permission = IsOwnerOrSuperuser()

    assert permission.has_object_permission(request, None, survey) is True

@pytest.mark.django_db
def test_isownerorsuperuser_denies_unsafe_methods_when_owner_does_not_exist(user_factory, api_rf, survey):
    stranger = user_factory('stranger')
    request = api_rf('delete', stranger)
    permission = IsOwnerOrSuperuser()

    assert permission.has_object_permission(request, None, survey) is False


    