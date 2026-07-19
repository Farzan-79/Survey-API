import pytest
from django.db.utils import IntegrityError
from survey.models import Survey, Question, Choice, Answer, Submission

@pytest.mark.django_db
def test_survey_save_generates_slug_from_title():
    survey = Survey.objects.create(title = 'My Cool Survey')
    assert survey.slug == 'my-cool-survey'

@pytest.mark.django_db
def test_same_user_cant_have_duplicate_survey_titles(user_factory):
    user_1 = user_factory('u1')
    user_2 = user_factory('u2')

    survey_1 = Survey.objects.create(title = 'My Cool Survey', user= user_1)
    survey_2 = Survey.objects.create(title = 'My Cool Survey', user= user_2)
    with pytest.raises(IntegrityError):
        survey_3 = Survey.objects.create(title = 'My Cool Survey', user= user_1)

@pytest.mark.django_db
def test_survey_slugs_are_not_duplicate(user_factory):
    user_1 = user_factory('u1')
    user_2 = user_factory('u2')
    user_3 = user_factory('u3')

    survey_1 = Survey.objects.create(title = 'My Cool Survey', user= user_1)
    survey_2 = Survey.objects.create(title = 'My Cool Survey', user= user_2)
    survey_3 = Survey.objects.create(title = 'My Cool Survey', user= user_3)

    assert survey_1.slug == "my-cool-survey"
    assert survey_2.slug == "my-cool-survey-1"
    assert survey_3.slug == "my-cool-survey-2"

@pytest.mark.django_db
def test_survey_str_returns_survey_title(survey):
    assert str(survey) == 'Base Survey'

@pytest.mark.django_db
def test_slug_doesnt_change_for_updates(survey):
    s1 = survey.slug
    survey.title = 'A New Title'
    survey.save()
    s2 = survey.slug
    assert s1 == s2 == 'base-survey'

@pytest.mark.django_db
def test_question_duplicate_title_raise_error_in_the_same_survey(survey):
    survey_2 = Survey.objects.create(title='Base 2')
    Question_1 = Question.objects.create(survey=survey, title='How Old Are You?', question_type='free_text')
    Question_2 = Question.objects.create(survey=survey_2, title='How Old Are You?', question_type='free_text')
    assert Question_1.survey == survey
    assert Question_2.survey == survey_2
    with pytest.raises(IntegrityError):
        Question_3 = Question.objects.create(survey=survey, title='How Old Are You?', question_type='free_text')

@pytest.mark.django_db
def test_question_str_returns_questions_title(question):
    assert str(question) == 'Pick One'

@pytest.mark.django_db
def test_choice_duplicate_title_raise_error_in_the_same_question(survey, question):
    question_2 = Question.objects.create(survey=survey, title='Pick Another', question_type='multiple_choice')
    choice_1 = Choice.objects.create(question=question, title='A')
    choice_2 = Choice.objects.create(question=question_2, title='A')
    with pytest.raises(IntegrityError):
        choice_3 = Choice.objects.create(question=question, title='A')

@pytest.mark.django_db
def test_survey_ordering_by_time_created():
    survey_1 = Survey.objects.create(title='s1')
    survey_2 = Survey.objects.create(title='s2')
    assert list(Survey.objects.all()) == [survey_1, survey_2]

@pytest.mark.django_db
def test_question_ordering_by_id(survey):
    question_1 = Question.objects.create(title='q1', survey=survey)
    question_2 = Question.objects.create(title='q2', survey=survey)

    assert list(Question.objects.all()) == [question_1, question_2]

@pytest.mark.django_db
def test_choice_ordering_by_id(question):
    choice_1 = Choice.objects.create(title='q1', question= question)
    choice_2 = Choice.objects.create(title='q2', question= question)

    assert list(Choice.objects.all()) == [choice_1, choice_2]

@pytest.mark.django_db
def test_unique_question_answer_for_each_submission(survey, question):
    question_2 = Question.objects.create(title='q2', survey=survey)

    submission_1 = Submission.objects.create(survey=survey)
    submission_2 = Submission.objects.create(survey=survey)

    answer_1 = Answer.objects.create(submission=submission_1, question=question)
    answer_2 = Answer.objects.create(submission=submission_1, question=question_2)
    answer_3 = Answer.objects.create(submission=submission_2, question=question)
    answer_4 = Answer.objects.create(submission=submission_2, question=question_2)
    with pytest.raises(IntegrityError):
        answer_5 = Answer.objects.create(submission=submission_2, question=question)

@pytest.mark.django_db
def test_survey_children_and_parent_relations_and_count(survey, question, choices, submission, answer):
    assert Survey.objects.count() == 1
    assert survey.questions.count() == 1
    assert question.answers.count() == 1
    assert question.choices.count() == 4
    assert survey.submissions.count() == 1
    assert submission.answers.count() == 1

@pytest.mark.django_db
def test_survey_children_CASCADE_on_delete(survey, question, choices, submission, answer):
    survey.delete()
    assert Question.objects.count() == 0
    assert Choice.objects.count() == 0
    assert Submission.objects.count() == 0
    assert Answer.objects.count() == 0

@pytest.mark.django_db
def test_question_children_CASCADE_on_delete(survey, question, choices, submission, answer):
    question.delete()
    assert Choice.objects.count() == 0
    assert Answer.objects.count() == 0

@pytest.mark.django_db
def test_choice_children_CASCADE_on_delete(survey, question, choices, submission, answer):
    choices.last().delete() # same choice as answer.chosen_choice, relies on ordering
    assert Answer.objects.count() == 0

@pytest.mark.django_db
def test_submission_children_CASCADE_on_delete(survey, question, choices, submission, answer):
    submission.delete()
    assert Answer.objects.count() == 0

@pytest.mark.django_db
def test_submissions_user_set_NULL_if_user_deleted(submission, user_factory):
    u1 = user_factory('u1')
    submission.user = u1
    submission.save()
    # assert submission.user.username == 'u1' #THIS IS TRUE
    u1.delete()
    submission.refresh_from_db()
    assert submission.user == None