from rest_framework.validators import UniqueValidator
from .models import Survey
from rest_framework.serializers import ValidationError



Survey_unq_validator = UniqueValidator(queryset=Survey.objects.all(), lookup='iexact', message='Duplicate Survey Name')

def validate_questions_payload(incoming_questions):
    if not incoming_questions:
        raise ValidationError({"questions": "A Survey must have at least one Question"},
                               code= "no_questions"
                               )
    q_titles = []
    for q in incoming_questions:
        qq = q.get('title')
        if qq in q_titles:
            raise ValidationError(
                {"questions": f"Duplicate question title in this survey: '{qq}'"},
                code = "duplicate_question_title"
                )
        q_titles.append(qq)
        if q.get('question_type') == 'multiple_choice':
            incoming_choices = q.get('choices', [])
            if len(incoming_choices) < 2:
                raise ValidationError(
                    {"choices":f"A Multiple-Choice Question can't have less than 2 choices: '{qq}'"},
                    code= "min_choices_required"
                    )
            c_titles = []
            for c in incoming_choices:
                cc = c.get('title')
                if cc in c_titles:
                    raise ValidationError(
                        {"choices": f"Duplicate choice in question '{qq}': '{cc}'"},
                        code= "duplicate_choice_title"
                        )
                c_titles.append(cc)
        elif q.get('question_type') == 'free_text':
            if q.get('choices'):
                raise ValidationError(
                    {"choices": f"A Free-Text Question can't accept choices: '{qq}'"},
                    code= "free_text_cannot_have_choices"
                    )