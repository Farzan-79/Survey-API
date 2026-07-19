import pytest
from unittest.mock import patch
from rest_framework.validators import ValidationError
from survey.models import Survey, Question, Choice, Answer, Submission
from survey.serializers import (
    AnswerSerializer,
    SubmissionSerializer,
    SurveyCreateSerializer,
    SurveyDetailSerializer,
    QuestionSerializer,
    SurveyResaultSerializer,
    QuestionResaultSerializer,
    ChoiceResaultSerializer,
    SurveyListSerializer,
    SurveyDetailReadSerializer,
    SurveyUpdateMessageSerializer,
    SurveyCreatedMessageSerializer,
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
def test_answer_serializer_rejects_empty_string_text_answer_in_free_text(survey, ft_question):
    serializer = AnswerSerializer(
        data= {'question': ft_question.id, 'text_answer': "  "},
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
def test_submission_serializer_rejects_missing_required_question(survey, question, ft_question, choices, api_rf):
    data = {'answers':[
        {'question': ft_question.id, 'text_answer': 'hello'}
    ]}
    request = api_rf('post', user=None)
    serializer = SubmissionSerializer(data=data, context={'survey':survey, 'request': request})
    assert serializer.is_valid() is False
    assert serializer.errors['answers'][0].code == 'missing_required_questions'

@pytest.mark.django_db
def test_submission_serializer_allows_missing_unrequired_question(survey, question, ft_question, choices, api_rf):
    ft_question.required = False
    ft_question.save()
    data = {'answers':[
        {'question': question.id, 'chosen_choice': choices.first().id}
    ]}
    request = api_rf('post', user=None)
    serializer = SubmissionSerializer(data=data, context={'survey':survey, 'request': request})
    assert serializer.is_valid(), serializer.errors

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
def test_survey_create_serializer_ignores_incoming_id(user_factory, survey, question, ft_question, choices):
    owner = user_factory('owner')
    payload = {
        'id': survey.id,
        'title': 'Survey',
        'description': 'just a survey',
        'questions': [
            {'id': question.id, 'title': 'q1', 'question_type': 'multiple_choice', 'choices': [{'id':choices.first().id, 'title': 'c1'}, {'id':choices.last().id,'title': 'c2'}]},
            {'id': ft_question.id, 'title': 'q2', 'question_type': 'free_text', 'required': False}
        ]
    }
    serializer = SurveyCreateSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors
    new_survey = serializer.save(user=owner)

    assert new_survey.id != survey.id #its 2, the fixture survey is 1

    new_question_ids = set(new_survey.questions.values_list('id', flat=True))
    assert question.id not in new_question_ids
    assert ft_question.id not in new_question_ids

    new_choice_ids = set(Choice.objects.filter(question__survey=new_survey).values_list('id', flat=True))
    assert choices.first().id not in new_choice_ids
    assert choices.last().id not in new_choice_ids

@pytest.mark.django_db
def test_create_serializer_requires_question(user_factory):
    owner = user_factory('owner')
    payload = {
        'title': 'Survey',
        'descriptions': 'just a survey'
    }
    serializer = SurveyCreateSerializer(data=payload)
    assert serializer.is_valid() is False
    assert serializer.errors['questions'][0].code == 'required'

@pytest.mark.django_db
def test_create_serializer_rejects_explicitly_empty_questions_list(user_factory):
    payload = {'title': 'Empty List Survey', 'description': '', 'questions': []}
    serializer = SurveyCreateSerializer(data=payload)
    assert serializer.is_valid() is False
    assert serializer.errors['questions'][0].code == 'no_questions'

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
def test_survey_create_serializer_rejects_case_insensitive_duplicate_title(user_factory):
    owner = user_factory('owner')
    Survey.objects.create(title='Customer Feedback', user=owner)
    data = {
        'title': 'customer feedback', 
        'description': '',
        'questions': [{'title': 'Q1', 'question_type': 'free_text', 'required': True}],
    }
    serializer = SurveyCreateSerializer(data=data, context={'user': owner})
    assert serializer.is_valid() is False
    assert serializer.errors['title'][0].code == 'unique'
    assert str(serializer.errors['title'][0]) == 'Duplicate Survey Name'

#! ================================================================
#!                    SurveyDetailSerializer
#! ================================================================

@pytest.mark.django_db
def test_detail_serializer_requires_instance():
    serializer = SurveyDetailSerializer(data= {'title': 'x', 'description': 'xx', 'questions': []})
    assert serializer.is_valid() is False
    assert serializer.errors['non_field_errors'][0].code == 'survey_not_found'
    assert str(serializer.errors['non_field_errors'][0]) == 'Survey Not Found'

@pytest.mark.django_db
def test_detail_serializer_freezes_questions_after_a_submission_but_updates_title_and_description(full_survey):
    Submission.objects.create(survey=full_survey)
    q2 = full_survey.questions.get(title='q2')
    data = {
        'title': 'updated title',
        'description': 'updated description',
        'questions': [{'id':q2.id, 'title':'q222', 'required':True, 'question_type': 'free_text'}]
    }
    serializer = SurveyDetailSerializer(instance=full_survey, data=data)
    assert serializer.is_valid(), serializer.errors
    assert serializer._frozen is True
    
    updated = serializer.save()

    #* title and description should be updated, questions and choices should be silently removed and remain unchanged.
    assert updated.title == 'updated title'
    assert updated.description == 'updated description' 
    assert updated.questions.count() == 2
    assert updated.questions.get(title='q1').choices.count() == 2
    #assert updated.questions.get(id=q2.id).title == 'q2'
    q2.refresh_from_db()
    assert q2.title == 'q2'

@pytest.mark.django_db
def test_update_serializer_rejects_explicitly_empty_questions_list(user_factory, survey, question):
    payload = {'title': 'Empty List Survey', 'description': '', 'questions': []}
    serializer = SurveyDetailSerializer(survey ,data=payload)
    assert serializer.is_valid() is False
    assert serializer.errors['questions'][0].code == 'no_questions'

@pytest.mark.django_db
def test_update_serializer_requires_question(user_factory, survey, question):
    payload = {'title': 'Empty List Survey', 'description': ''}
    serializer = SurveyDetailSerializer(survey ,data=payload)
    assert serializer.is_valid() is False
    assert serializer.errors['questions'][0].code == 'required'

@pytest.mark.django_db
def test_detail_serializer_adds_a_new_question(full_survey):
    q1 = full_survey.questions.get(title='q1')
    q2 = full_survey.questions.get(title='q2')
    data = {
        'title': full_survey.title, 'description': '',
        'questions': [
            {'id': q1.id, 'title': q1.title, 'question_type': q1.question_type,
             'choices': [{'id': c.id, 'title': c.title} for c in q1.choices.all()]},
            {'id': q2.id, 'title': q2.title, 'question_type': q2.question_type, 'required': False},
            {'title': 'Q3 new', 'question_type': 'free_text'},   # no id -> created
        ]
    }
    serializer = SurveyDetailSerializer(full_survey, data=data)
    assert serializer.is_valid(), serializer.errors
    updated = serializer.save()

    assert updated.questions.count() == 3
    assert updated.questions.filter(title='Q3 new').exists()
    assert updated.questions.get(title=q2.title).required == False

@pytest.mark.django_db
def test_detail_serializer_deletes_question(full_survey):
    q1 = full_survey.questions.get(title='q1')
    data = {
        'title': full_survey.title, 'description': '',
        'questions': [
            {'id': q1.id, 'title': q1.title, 'question_type': q1.question_type,
             'choices': [{'id': c.id, 'title': c.title} for c in q1.choices.all()]},
        ]
    }
    serializer = SurveyDetailSerializer(full_survey, data=data)
    assert serializer.is_valid(), serializer.errors
    updated = serializer.save()

    assert updated.questions.count() == 1
    assert not updated.questions.filter(title='q2').exists()

@pytest.mark.django_db
def test_detail_serializer_adds_updates_deletes_choices(full_survey):
    q1 = full_survey.questions.get(title='q1')
    q2 = full_survey.questions.get(title='q2')
    data = {
        'title': full_survey.title, 'description': '',
        'questions': [
            {'id': q1.id, 'title': q1.title, 'question_type': q1.question_type,
             'choices': [
                 {'id': q1.choices.get(title='c1').id, 'title': 'c11'},
                 {'title': 'c3 new'},
                 {'title': 'c4 new'}
             ]},
            {'id': q2.id, 'title': q2.title, 'question_type': q2.question_type},
        ]
    }
    serializer = SurveyDetailSerializer(full_survey, data=data)
    assert serializer.is_valid(), serializer.errors
    updated = serializer.save()

    assert updated.questions.count() == 2
    q1.refresh_from_db()
    assert not q1.choices.filter(title='c2').exists()
    assert set(q1.choices.values_list('title', flat=True)) == {'c11', 'c3 new', 'c4 new'}

@pytest.mark.django_db
def test_detail_serializer_edits_everything_all_at_once(full_survey):
    q1 = full_survey.questions.get(title='q1')
    q2 = full_survey.questions.get(title='q2')
    q3 = Question.objects.create(survey=full_survey, title='q3', question_type='free_text', required=False)
    data = {
        'title': 'new title', 'description': 'meow',
        'questions': [
            {'id': q1.id, 'title': 'q1 new', 'question_type': q1.question_type,
             'choices': [{'id': q1.choices.first().id, 'title': 'c1 new'}, {'title': 'c3'}]},
            {'id': q3.id, 'title': 'q3 updated', 'question_type': 'multiple_choice', 'required': False, 'choices': [{'title': 'c1 new'}, {'title': 'c2'}]},
            {'title': 'q4', 'question_type': 'free_text'}
        ]
    }
    serializer = SurveyDetailSerializer(full_survey, data=data)
    assert serializer.is_valid(), serializer.errors
    updated = serializer.save()

    assert updated.title == 'new title'
    assert updated.description == 'meow'
    assert not updated.questions.filter(title='q2').exists()
    assert set(updated.questions.values_list('title', flat=True)) == {'q1 new', 'q3 updated', 'q4'}
    assert set(updated.questions.get(title='q1 new').choices.values_list('title', flat=True)) == {'c1 new', 'c3'}
    assert updated.questions.get(title='q3 updated').question_type == 'multiple_choice'
    assert set(updated.questions.get(title='q3 updated').choices.values_list('title', flat=True)) == {'c1 new', 'c2'}
    assert updated.questions.get(title= 'q3 updated').required == False
    assert updated.questions.get(title='q4').required == True

@pytest.mark.django_db
def test_detail_serializer_rejects_question_id_from_another_survey(full_survey):
    another_survey = Survey.objects.create(title= 'another survey')
    alien_question = Question.objects.create(survey= another_survey, title='alien', question_type= 'free_text')
    q1 = full_survey.questions.get(title='q1')

    data = {
        'title': full_survey.title,
        'description': full_survey.description,
        'questions': [
            {'id': q1.id, 'title': q1.title, 'question_type': q1.question_type,
             'choices': [
                 {'id': q1.choices.get(title='c1').id, 'title': 'c11'},
                 {'title': 'c3 new'},
                 {'title': 'c4 new'}
             ]},
            {'id': alien_question.id, 'title': 'sus q', 'question_type':'free_text'}
        ]
    }
    serializer = SurveyDetailSerializer(full_survey, data=data)
    assert serializer.is_valid() is False
    assert serializer.errors['questions'][0].code == 'invalid_question_id'

@pytest.mark.django_db
def test_detail_serializer_rejects_invalid_choice_id_from_another_question_in_same_survey(full_survey):
    q3 = Question.objects.create(survey=full_survey, title='q3', question_type= 'multiple_choice')
    c_q3 = Choice.objects.create(question= q3, title='c_q3')
    q1 = full_survey.questions.get(title='q1')
    
    data = {
        'title': full_survey.title,
        'description': full_survey.description,
        'questions': [
            {'id': q1.id, 'title': q1.title, 'question_type': q1.question_type,
             'choices': [
                 {'id': q1.choices.get(title='c1').id, 'title': 'c11'},
                 {'id': c_q3.id, 'title': 'sus'}
             ]}]
    }
    serializer = SurveyDetailSerializer(full_survey, data=data)
    assert serializer.is_valid() is False
    assert serializer.errors['choices'][0].code == 'choice_id_mismatch_question_id'

@pytest.mark.django_db
def test_detail_serializer_rejects_invalid_choice_id_or_from_another_survey(full_survey):
    another_survey = Survey.objects.create(title='another survey')
    q3 = Question.objects.create(survey=another_survey, title='q3', question_type= 'multiple_choice')
    c_q3 = Choice.objects.create(question= q3, title='c_q3')
    q1 = full_survey.questions.get(title='q1')
    
    data = {
        'title': full_survey.title,
        'description': full_survey.description,
        'questions': [
            {'id': q1.id, 'title': q1.title, 'question_type': q1.question_type,
             'choices': [
                 {'id': q1.choices.get(title='c1').id, 'title': 'c11'},
                 {'id': c_q3.id, 'title': 'sus'}
             ]}]
    }
    serializer = SurveyDetailSerializer(full_survey, data=data)
    assert serializer.is_valid() is False
    assert serializer.errors['choices'][0].code == 'invalid_choice_id'

@pytest.mark.django_db
def test_detail_serializer_rejects_choice_id_without_parent_question_id(full_survey):
    q1 = full_survey.questions.get(title='q1')
    c1 = q1.choices.get(title='c1')

    data = {
        'title': full_survey.title, 'description': '',
        'questions': [
            {'title': 'New Q shell', 'question_type': 'multiple_choice',   # no 'id' on the question
             'choices': [{'id': c1.id, 'title': 'A'}, {'title': 'New Choice'}]},
        ]
    }
    serializer = SurveyDetailSerializer(full_survey, data=data)
    assert serializer.is_valid() is False
    assert serializer.errors['choices'][0].code == 'question_id_not_provided'

@pytest.mark.django_db
def test_survey_detail_read_serialiezer_uses_prefetched_questions(survey, question, ft_question, api_rf, user_factory):
    survey.prefetched_questions = Question.objects.filter(title='Pick One')
    user = user_factory('user')
    survey.user = user
    survey.save()
    request = api_rf('get', user)

    data = SurveyDetailReadSerializer(survey, context={'request': request}).data

    assert len(data['questions']) == 1 # does not hit the db, uses prefetched, and there is only one question
    
    del survey.prefetched_questions
    data_2 = SurveyDetailReadSerializer(survey, context={'request': request}).data

    assert len(data_2['questions']) == 2 # prefetch deleted, now it uses db

@pytest.mark.django_db
def test_detail_serializer_hides_user_for_owner(survey, question, api_rf, user_factory):
    owner = user_factory('owner')
    survey.user = owner
    survey.save()

    request = api_rf('get', owner)
    response = SurveyDetailSerializer(survey, context={'request': request})

    assert 'user' not in response.data

@pytest.mark.django_db
def test_detail_serializer_hides_user_for_owner(survey, question, api_rf, user_factory):
    owner = user_factory('owner')
    survey.user = owner
    admin = user_factory('admin')
    admin.is_superuser = True
    admin.save()
    survey.save()

    request = api_rf('get', admin)
    response = SurveyDetailSerializer(survey, context={'request': request})

    assert 'user' in response.data

#! ================================================================
#!                  Representaion Serializers
#! ================================================================

#? -------------- detail serializers --------------------

@pytest.mark.django_db
def test_question_serializer_include_choices_in_multiple_choice_questions(question, choices):
    serializer = QuestionSerializer(question)
    data = serializer.data

    assert data['question_type'] == 'multiple_choice'
    assert 'choices' in data
    assert len(data['choices']) == 4

@pytest.mark.django_db
def test_question_serializer_does_not_include_choices_in_free_text_questions(ft_question, choices):
    serializer = QuestionSerializer(ft_question)
    data = serializer.data

    assert data['question_type'] == 'free_text'
    assert 'choices' not in data

#? -------------- resault serializers --------------------

@pytest.mark.django_db
def test_question_resault_serializer_include_choices_in_multiple_choice_questions(question, choices):
    serializer = QuestionResaultSerializer(question)
    data = serializer.data

    assert data['question_type'] == 'multiple_choice'
    assert 'choices' in data
    assert 'text_answers' not in data
    assert len(data['choices']) == 4

@pytest.mark.django_db
def test_question_resault_serializer_does_not_include_choices_in_free_text_questions(ft_question, choices):
    serializer = QuestionResaultSerializer(ft_question)
    data = serializer.data

    assert data['question_type'] == 'free_text'
    assert 'choices' not in data
    assert 'text_answers' in data

@pytest.mark.django_db
def test_choice_result_serializer_calculates_percentage(survey, question, choices):
    choice = choices.first()
    choice.times_selected = 4
    context = {
        'times_answered_question': 10
    }

    data = ChoiceResaultSerializer(choice, context=context).data

    assert data['percentage'] == 40

@pytest.mark.django_db
def test_choice_result_serializer_calculates_percentage_when_there_is_no_answer(survey, question, choices):
    choice = choices.first()

    data = ChoiceResaultSerializer(choice).data

    assert data['percentage'] == 0

@pytest.mark.django_db
def test_choice_result_serializer_shows_text_answers_in_free_text_question(survey, ft_question):
    submission = Submission.objects.create(survey=survey)
    answer = Answer.objects.create(question=ft_question, text_answer='hello', submission=submission)
    serializer = QuestionResaultSerializer(ft_question)
    data = serializer.data

    assert data['text_answers'] == ['hello']

@pytest.mark.django_db
def test_survey_resault_serializer_shows_all_questions_and_counts(survey, question, ft_question, choices):
    submission = Submission.objects.create(survey=survey)
    answer_1 = Answer.objects.create(question= question, submission= submission, chosen_choice= choices.first())
    answer_2 = Answer.objects.create(question= ft_question, submission= submission, text_answer='hello')

    data = SurveyResaultSerializer(survey).data
    questions = data['questions']

    assert len(questions) == 2
    assert questions[0]['choices'][0]['percentage'] == 100 
    assert questions[0]['choices'][1]['percentage'] == 0 
    assert 'hello' in questions[1]['text_answers']
    assert data['total_responses'] == 1

#? ---------------- list serializer -----------------------

@pytest.mark.django_db
def test_survey_list_serializer_uses_annotated_counts(survey, question, user_factory, api_rf):
    survey.question_count = 999 #the serializer should use this instead of calling the db itself. the view provides it
    survey.submission_count = 888
    user = user_factory('user')
    request = api_rf('get', user=user)
    data = SurveyListSerializer(survey, context={'request':request}).data

    assert data['total_responses'] == 888
    assert data['question_count'] == 999

@pytest.mark.django_db
def test_survey_list_serializer_hides_user_for_all_but_superuser(survey, question, user_factory, api_rf):
    user = user_factory('regular user')
    suser = user_factory('super user')
    suser.is_superuser = True

    survey.user = user
    survey.save()
    request = api_rf('get', user=user)
    srequest = api_rf('get', user=suser)

    ulist = SurveyListSerializer(Survey.objects.filter(user=user) ,many=True, context={'request': request}).data
    slist = SurveyListSerializer(Survey.objects.all() ,many=True, context={'request': srequest}).data

    assert 'user' not in ulist[0]
    assert 'user' in slist[0]

#? ---------------- message serializer -----------------------

@pytest.mark.django_db
def test_update_message_serializer_returns_right_message(survey, question, ft_question, api_rf):
    request = api_rf('get', None)
    data = SurveyUpdateMessageSerializer(survey, context={'request': request, 'question_count': 987}).data

    assert data['message'] == 'Survey Updated Successfully: Base Survey'
    assert data['question_count'] == 987

    data_2 = SurveyUpdateMessageSerializer(survey, context={'request': request, 'frozen': True}).data

    assert data_2['message'] == f'This Survey is Frozen because it has already been answered: {survey.title} \n Only the title and Description were updated'
    assert data_2['question_count'] == 2

@pytest.mark.django_db
def test_created_message_serializer_returns_right_message(survey, question, ft_question, api_rf):
    request = api_rf('get', None)
    data = SurveyCreatedMessageSerializer(survey, context={'request': request, 'question_count': 456}).data

    assert data['message'] == f'Your Survey has been saved successfuly: {survey.title}'
    assert data['question_count'] == 456

    data_2 = SurveyCreatedMessageSerializer(survey, context={'request': request}).data

    assert data_2['question_count'] == 2
