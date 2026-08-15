from rest_framework import permissions
from survey.models import Survey

class IsOwnerOrReadOnlyPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user or request.user.is_superuser
    
class IsOwnerOrSuperuser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return obj.user_id == user.id or user.is_superuser

class PrivateSurveyPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        slug = view.kwargs.get('slug')

        if not slug:
            return True

        try:
            survey = Survey.objects.get(slug=slug)
        except Survey.DoesNotExist:
            return True

        return survey.is_public or request.user.is_authenticated