import pytest
from unittest.mock import patch
from rest_framework.validators import ValidationError
from survey.models import Survey, Question, Choice, Answer, Submission
from survey.serializers import (
    AnswerSerializer,
    SubmissionSerializer,
    SurveyCreateSerializer,
    SurveyDetailSerializer
)

#! ================================================================
#!                      AnswerSerializer
#! ================================================================

#? -------------- multiple choice questions ---------------

@pytest.mark.django_db
def test_answer_serializer_valid_for_multiple_choice(survey, question, choices):
    serializer = AnswerSerializer(
        data= {'question': question.id, 'chosen_choice': choices.last().id},
        context= {'survey': survey}
    )
    assert serializer.is_valid(), serializer.errors

@pytest.mark.django_db
def test_answer_serializer_requires_chosen_choice_in_multiple_choice(survey, question, choices):
    serializer = AnswerSerializer(
        data= {'question': question.id, 'chosen_choice': None},
        context= {'survey': survey}
    )
    assert serializer.is_valid() is False
    assert serializer.errors['chosen_choice'][0].code == 'choice_required_for_multiple_choice'

@pytest.mark.django_db
def test_answer_serializer_rejects_text_answer_in_multiple_choice(survey, question, choices):
    serializer = AnswerSerializer(
        data= {'question': question.id, 'chosen_choice': choices.first().id, 'text_answer': 'hello'},
        context= {'survey': survey}
    )
    assert serializer.is_valid() is False
    assert serializer.errors['text_answer'][0].code == 'text_answer_not_allowed_for_multiple_choice'

@pytest.mark.django_db
def test_answer_serializer_rejects_chosen_choice_from_another_survey(survey, question):
    another_survey = Survey.objects.create(title= 'another survey')
    another_question = Question.objects.create(
        survey = another_survey,
        title = 'another question',
        question_type = 'multiple_choice',
        )
    another_choice = Choice.objects.create(title= 'A', question=another_question)

    serializer = AnswerSerializer(
        data= {'question': question.id, 'chosen_choice': another_choice.id},
        context= {'survey': survey}
    )
    assert serializer.is_valid() is False
    # Rejected at the FIELD level, before .validate() runs at all - the
    # `chosen_choice` queryset was already scoped to Choice.objects.filter(question__survey= survey) in
    # __init__, so another_choice.id simply isn't a valid choice for this field.
    assert serializer.errors['chosen_choice'][0].code == 'does_not_exist'

@pytest.mark.django_db
def test_answer_serializer_rejects_chosen_choice_from_another_question(survey, choices):
    another_question = Question.objects.create(
        survey = survey,
        title = 'question 2',
        question_type = 'multiple_choice',
        )
    serializer = AnswerSerializer(
        data= {'question': another_question.id, 'chosen_choice': choices.first().id},
        context= {'survey': survey}
    )
    assert serializer.is_valid() is False
    assert serializer.errors['chosen_choice'][0].code == 'choice_does_not_belong_to_declared_question'

#? -------------- free text questions --------------------

@pytest.mark.django_db
def test_answer_serializer_valid_for_free_text(survey, ft_question):
    serializer = AnswerSerializer(
        data= {'question': ft_question.id, 'text_answer': 'hello'},
        context= {'survey': survey}
    )
    assert serializer.is_valid(), serializer.errors

@pytest.mark.django_db
def test_answer_serializer_requires_text_answer_in_free_text(survey, ft_question):
    serializer = AnswerSerializer(
        data= {'question': ft_question.id},
        context= {'survey': survey}
    )
    assert serializer.is_valid() is False
    assert serializer.errors['text_answer'][0].code == 'text_answer_required_for_free_text'

@pytest.mark.django_db
def test_answer_serializer_rejects_chosen_choice_in_free_text(survey, ft_question, choices):
    serializer = AnswerSerializer(
        data= {'question': ft_question.id, 'chosen_choice': choices.last().id, 'text_answer': 'hello'},
        context= {'survey': survey}
    )
    assert serializer.is_valid() is False
    assert serializer.errors['chosen_choice'][0].code == 'chosen_choice_not_allowed_for_free_text'

#? ---------------------- general -------------------------

@pytest.mark.django_db
def test_answer_serializer_rejects_invalid_question_type(survey, choices):
    # Model-level `choices=` isn't enforced by .save() (only by
    # full_clean(), which ModelSerializer never calls) - so this row is
    # legal to create directly even though the API could never produce it.
    weird_question = Question.objects.create(
        survey=survey,
        title= 'weired Q',
        question_type= 'wrong'
    )
    serializer = AnswerSerializer(
        data= {'question': weird_question.id, 'chosen_choice': choices.first().id},
        context= {'survey': survey}
    )
    assert serializer.is_valid() is False
    assert serializer.errors['question'][0].code == 'unsupported_question_type'

@pytest.mark.django_db
def test_answer_serializer_rejects_questions_from_another_survey(survey, question, choices):
    another_survey = Survey.objects.create(title='another survey')
    another_qeustion = Question.objects.create(
        title= 'another question',
        survey= another_survey,
        question_type= 'free_text'
        )
    serializer = AnswerSerializer(
        data= {'question': another_qeustion.id, 'text_answer': 'hello'},
        context= {'survey': survey}
    )
    assert serializer.is_valid() is False
    # Rejected at the FIELD level, before .validate() runs at all - the
    # `question` queryset was already scoped to survey.questions.all() in
    # __init__, so foreign_question.id simply isn't a valid choice for this field.
    assert serializer.errors['question'][0].code == 'does_not_exist'

#! ================================================================
#!                   SubmissionSerializer
#! ================================================================

@pytest.mark.django_db
def test_submission_serializer_creates_submissions_with_answers(survey, question, ft_question, choices, api_rf):
    data = {'answers':[
        {'question': question.id, 'chosen_choice': choices.first().id},
        {'question': ft_question.id, 'text_answer': 'hello'}
    ]}
    request = api_rf('post', user=None)
    serializer = SubmissionSerializer(data=data, context={'request': request, 'survey': survey})
    
    assert serializer.is_valid(), serializer.errors

    submission = serializer.save()

    assert submission.survey_id == survey.id
    assert submission.answers.count() == 2
    assert submission.user == None

@pytest.mark.django_db
def test_submission_serializer_creates_submissions_with_answers(survey, question, ft_question, choices, api_rf):
    data = {'answers':[
        {'question': question.id, 'chosen_choice': choices.first().id}
    ]}
    request = api_rf('post', user=None)
    serializer = SubmissionSerializer(data=data, context={'survey':survey, 'request': request})
    assert serializer.is_valid() is False
    assert serializer.errors['answers'][0].code == 'missing_required_questions'

@pytest.mark.django_db
def test_submission_serializer_rejects_multiple_answers_for_a_question(survey, question, choices, api_rf):
    data = {'answers':[
        {'question': question.id, 'chosen_choice': choices.first().id},
        {'question': question.id, 'chosen_choice': choices.last().id}
    ]}
    request = api_rf('post', user=None)
    serializer = SubmissionSerializer(data=data, context={'survey':survey, 'request': request})
    assert serializer.is_valid() is False
    assert serializer.errors['answers'][0].code == 'question_answered_multiple_times_not_allowed'

@pytest.mark.django_db
def test_submission_serializer_allows_multiple_anonymous_answers(survey, question, choices, api_rf):
    first_answer_data = {'answers':[{'question': question.id, 'chosen_choice': choices.first().id}]}
    second_answer_data = {'answers':[{'question': question.id, 'chosen_choice': choices.first().id}]}
    third_answer_data = {'answers':[{'question': question.id, 'chosen_choice': choices.last().id}]}
    request = api_rf('post', user=None)

    serializer_1 = SubmissionSerializer(data=first_answer_data, context={'request':request, 'survey': survey})
    serializer_2 = SubmissionSerializer(data=second_answer_data, context={'request':request, 'survey': survey})
    serializer_3 = SubmissionSerializer(data=third_answer_data, context={'request':request, 'survey': survey})

    assert serializer_1.is_valid(), serializer_1.errors
    serializer_1.save()
    assert serializer_2.is_valid(), serializer_2.errors
    serializer_2.save()
    assert serializer_3.is_valid(), serializer_3.errors
    serializer_3.save()

    assert Submission.objects.filter(survey=survey).count() == 3
    
@pytest.mark.django_db
def test_submission_serializer_rejects_multiple_authenticated_user_answers(survey, question, choices, api_rf, user_factory):
    data = {'answers':[{'question': question.id, 'chosen_choice': choices.first().id}]}
    data_2 = {'answers':[{'question': question.id, 'chosen_choice': choices.last().id}]}
    user = user_factory('user')
    request = api_rf('post', user=user)

    serializer = SubmissionSerializer(data=data, context={'survey':survey, 'request':request})
    assert serializer.is_valid(), serializer.errors
    serializer.save()

    serializer_2 = SubmissionSerializer(data=data_2, context={'survey':survey, 'request':request})
    assert serializer_2.is_valid(), serializer_2.errors #* still passes, the error comes from create(), not validate()
        
    #* the last method can't be used here, as it is not coming from validate() and has a different format.
    #* its not a list like before, we use .value.detail like this:
    with pytest.raises(ValidationError) as error_info:
        serializer_2.save()

    assert error_info.value.detail[0].code == 'duplicate_submission'

@pytest.mark.django_db
def test_submission_serializer_integrity_error_backstop_for_race_condition(survey, question, choices, user_factory, api_rf):
    user = user_factory('submitter')
    # Simulates another, near-simultaneous request that already got its
    # Submission row inserted - the exact scenario the .filter().exists()
    # check exists to catch, but can miss if two requests both read "no
    # submission yet" before either has written.
    Submission.objects.create(survey=survey, user=user)

    request = api_rf('post', user=user)
    data = {'answers':[{'question': question.id, 'chosen_choice': choices.first().id}]}
    serializer = SubmissionSerializer(data=data, context={'request': request, 'survey': survey})
    assert serializer.is_valid(), serializer.errors

    # Force the fast-path check to lie and say "no duplicate exists" -
    # recreating the race window artificially, so the only thing left to
    # catch the real duplicate is the DB constraint + the new try/except.
    # patch() targets the path where Submission is actually *used*
    # (survey.serializers), not where it's defined (survey.models) - that's
    # the standard rule for where to point a mock.patch() string.
    with patch('survey.serializers.Submission.objects.filter') as mock_filter:
        mock_filter.return_value.exists.return_value = False
        with pytest.raises(ValidationError) as err_info:
            serializer.save()
    
    assert err_info.value.detail[0].code == 'duplicate_submission'


#! ================================================================
#!                    SurveyCreateSerializer
#! ================================================================

@pytest.mark.django_db
def test_create_serializer_creates_survey_with_nested_questions_and_choices(user_factory):
    owner = user_factory('owner')
    payload = {
        'title': 'Survey',
        'descriptions': 'just a survey',
        'questions': [
            {'title': 'q1', 'question_type': 'multiple_choice', 'choices': [{'title': 'c1'}, {'title': 'c2'}]},
            {'title': 'q2', 'question_type': 'free_text', 'required': False}
        ]
    }
    serializer = SurveyCreateSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors
    survey = serializer.save(user=owner)

    assert survey.user_id == owner.id
    assert survey.questions.count() == 2
    assert survey.questions.filter(required=True).count() == 1
    assert survey.questions.get(title='q1').choices.count() == 2

@pytest.mark.django_db
def test_create_serializer_requires_at_least_one_question(user_factory):
    owner = user_factory('owner')
    payload = {
        'title': 'Survey',
        'descriptions': 'just a survey'
    }
    serializer = SurveyCreateSerializer(data=payload)
    assert serializer.is_valid() is False
    assert serializer.errors['questions'][0].code == 'required'


@pytest.mark.django_db
def test_create_serializer_rejects_duplicate_question_titles(user_factory):
    owner = user_factory('owner')
    payload = {
        'title': 'Survey',
        'descriptions': 'just a survey',
        'questions': [
            {'title': 'q1', 'question_type': 'multiple_choice', 'choices': [{'title': 'c1'}, {'title': 'c2'}]},
            {'title': 'q1', 'question_type': 'free_text', 'required': False}
        ]
    }
    serializer = SurveyCreateSerializer(data=payload)
    assert serializer.is_valid() is False
    assert serializer.errors['questions'][0].code == 'duplicate_question_title'

@pytest.mark.django_db
def test_create_serializer_rejects_fewer_than_two_choices_on_multiple_choice_question(user_factory):
    owner = user_factory('owner')
    payload = {
        'title': 'Survey',
        'descriptions': 'just a survey',
        'questions': [
            {'title': 'q1', 'question_type': 'multiple_choice', 'choices': [{'title': 'c1'}]}
        ]
    }
    serializer = SurveyCreateSerializer(data=payload)
    assert serializer.is_valid() is False
    assert serializer.errors['choices'][0].code == 'min_choices_required'

@pytest.mark.django_db
def test_create_serializer_rejects_duplicate_choice_title_on_the_same_question(user_factory):
    owner = user_factory('owner')
    payload = {
        'title': 'Survey',
        'descriptions': 'just a survey',
        'questions': [
            {'title': 'q1', 'question_type': 'multiple_choice', 'choices': [{'title': 'c1'}, {'title': 'c1'}]}
        ]
    }
    serializer = SurveyCreateSerializer(data=payload)
    assert serializer.is_valid() is False
    assert serializer.errors['choices'][0].code == 'duplicate_choice_title'

@pytest.mark.django_db
def test_create_serializer_allows_duplicate_choice_title_on_different_question(user_factory):
    owner = user_factory('owner')
    payload = {
        'title': 'Survey',
        'descriptions': 'just a survey',
        'questions': [
            {'title': 'q1', 'question_type': 'multiple_choice', 'choices': [{'title': 'c1'}, {'title': 'c2'}]},
            {'title': 'q2', 'question_type': 'multiple_choice', 'choices': [{'title': 'c1'}, {'title': 'c2'}]}

        ]
    }
    serializer = SurveyCreateSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors

@pytest.mark.django_db
def test_create_serializer_rejects_choices_on_free_text_questions(user_factory):
    owner = user_factory('owner')
    payload = {
        'title': 'Survey',
        'descriptions': 'just a survey',
        'questions': [
            {'title': 'q1', 'question_type': 'free_text', 'choices': [{'title': 'c1'}]}
        ]
    }
    serializer = SurveyCreateSerializer(data=payload)
    assert serializer.is_valid() is False
    assert serializer.errors['choices'][0].code == 'free_text_cannot_have_choices'

@pytest.mark.django_db
def test_survey_create_serializer_rejects_case_insensitive_duplicate_title():
    Survey.objects.create(title='Customer Feedback')
    data = {
        'title': 'customer feedback', 
        'description': '',
        'questions': [{'title': 'Q1', 'question_type': 'free_text', 'required': True}],
    }
    serializer = SurveyCreateSerializer(data=data)
    assert serializer.is_valid() is False
    assert serializer.errors['title'][0].code == 'unique'
    assert str(serializer.errors['title'][0]) == 'Duplicate Survey Name'

#! ================================================================
#!                    SurveyDetailSerializer
#! ================================================================

