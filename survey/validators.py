from rest_framework.validators import UniqueValidator
from .models import Survey

Survey_unq_validator = UniqueValidator(queryset=Survey.objects.all(), lookup='iexact', message='Duplicate Survey Name')
