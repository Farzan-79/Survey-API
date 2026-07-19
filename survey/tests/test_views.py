import pytest
from rest_framework import status
from django.urls import reverse
from survey.models import Survey, Question, Choice, Submission

#! ================================================================
#!                    SurveyListCreateView
#! ================================================================

#? -------------- authentication / permissions ---------------

@pytest.mark.django_db
def test_list_create_view_denies_anonymous_get(api_client):
    url = reverse('survey:list-create')
    response = api_client.get(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_list_create_view_denies_anonymous_post(api_client):
    url = reverse('survey:list-create')
    payload = {'title': 'New Survey', 'questions': [{'title': 'q1', 'question_type': 'free_text'}]}
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_list_create_view_rejects_put(api_client, user_factory):
    user = user_factory('user')
    api_client.force_authenticate(user)
    url = reverse('survey:list-create')
    response = api_client.put(url, {}, 'json')

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

#? ---------------------- GET = List --------------------------

@pytest.mark.django_db
def test_list_view_returns_only_own_surveys_for_regular_user(api_client, user_factory, survey):
    owner = user_factory('owner')
    another_user = user_factory('user')
    url = reverse('survey:list-create')
    Survey.objects.create(user=owner, title='Owner Survey')

    # Owner GET
    api_client.force_authenticate(owner)
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    titles = [item['title'] for item in response.data]
    assert titles == ['Owner Survey']

    # another user GET
    api_client.force_authenticate(another_user)
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    titles = [item['title'] for item in response.data]
    assert titles == []

@pytest.mark.django_db
def test_list_view_returns_all_surveys_for_superuser(api_client, user_factory, survey):
    owner = user_factory('owner')
    admin = user_factory('admin')
    admin.is_superuser = True
    admin.save()
    url = reverse('survey:list-create')
    Survey.objects.create(user=owner, title='Owner Survey')
    Survey.objects.create(user=admin, title='Admin Survey')

    api_client.force_authenticate(admin)
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    titles = [item['title'] for item in response.data]
    assert titles == ['Base Survey', 'Owner Survey', 'Admin Survey']

@pytest.mark.django_db
def test_list_view_hides_user_field_for_non_superuser_user_and_shows_for_superuser(api_client, user_factory):
    owner = user_factory('owner')
    admin = user_factory('admin')
    admin.is_superuser = True
    admin.save()
    url = reverse('survey:list-create')
    Survey.objects.create(user=owner, title='Owner Survey')

    api_client.force_authenticate(admin)
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert 'user' in response.data[0] # shows it for admin

    api_client.force_authenticate(owner)
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert 'user' not in response.data[0] # hides it for owner (regular user)

@pytest.mark.django_db
def test_list_view_annotated_question_and_submission_counts(api_client, user_factory, survey, question, ft_question):
    owner = user_factory('owner')
    user = user_factory('user')
    survey.user = owner
    survey.save()
    Submission.objects.create(user=user, survey=survey)

    url = reverse('survey:list-create')
    Survey.objects.create(user=owner, title='Owner Survey')

    api_client.force_authenticate(owner)
    response = api_client.get(url)

    assert response.data[0]['question_count'] == 2
    assert response.data[0]['total_responses'] == 1

#? ---------------------- POST = Create --------------------------

@pytest.mark.django_db
def test_create_view_creates_survey_with_logged_in_user(user_factory, api_client):
    owner = user_factory('owner')
    api_client.force_authenticate(owner)
    payload = {
        'title': 'new survey',
        'questions': [
            {'title': 'q1', 'question_type': 'free_text'}
        ]
    }
    url = reverse('survey:list-create')
    response = api_client.post(url, data=payload, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    survey = Survey.objects.get(title='new survey')
    assert survey.questions.count() == 1
    assert survey.user.id == owner.id

@pytest.mark.django_db
def test_create_view_success_message_response_shape(user_factory, api_client):
    owner = user_factory('owner')
    api_client.force_authenticate(owner)
    payload = {
        'title': 'new survey',
        'questions': [
            {'title': 'q1', 'question_type': 'free_text'},
            {'title': 'q2', 'question_type': 'multiple_choice', 'choices':[{'title': 'c1'}, {'title': 'c2'}]}
        ]
    }
    url = reverse('survey:list-create')
    response = api_client.post(url, data=payload, format='json')
    
    assert response.status_code == status.HTTP_201_CREATED
    survey = Survey.objects.get(title='new survey')
    assert survey.title in response.data['message']
    assert response.data['question_count'] == 2
    assert 'detail_url' in response.data
    assert 'response_url' in response.data

@pytest.mark.django_db
def test_create_view_rejects_payload_without_questions(user_factory, api_client):
    owner = user_factory('owner')
    api_client.force_authenticate(owner)
    payload = {
        'title': 'new survey',
    }
    url = reverse('survey:list-create')
    response = api_client.post(url, data=payload, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_create_view_rejects_payload_with_questions_with_less_than_min_choices(user_factory, api_client):
    owner = user_factory('owner')
    api_client.force_authenticate(owner)
    payload = {
        'title': 'new survey',
        'questions': [
            {'title': 'q1', 'question_type': 'free_text'},
            {'title': 'q2', 'question_type': 'multiple_choice', 'choices':[{'title': 'c1'}]}
        ]
    }
    url = reverse('survey:list-create')
    response = api_client.post(url, data=payload, format='json')
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_create_view_rejects_payload_with_duplicate_question_title(user_factory, api_client):
    owner = user_factory('owner')
    api_client.force_authenticate(owner)
    payload = {
        'title': 'new survey',
        'questions': [
            {'title': 'q1', 'question_type': 'free_text'},
            {'title': 'q1', 'question_type': 'multiple_choice', 'choices':[{'title': 'c1'}, {'title': 'c2'}]}
        ]
    }
    url = reverse('survey:list-create')
    response = api_client.post(url, data=payload, format='json')
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_create_view_rejects_payload_with_duplicate_choice_title(user_factory, api_client):
    owner = user_factory('owner')
    api_client.force_authenticate(owner)
    payload = {
        'title': 'new survey',
        'questions': [
            {'title': 'q1', 'question_type': 'free_text'},
            {'title': 'q2', 'question_type': 'multiple_choice', 'choices':[{'title': 'c1'}, {'title': 'c1'}]}
        ]
    }
    url = reverse('survey:list-create')
    response = api_client.post(url, data=payload, format='json')
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_create_view_rejects_duplicate_title_with_the_same_user(user_factory, api_client):
    owner = user_factory('owner')
    api_client.force_authenticate(owner)
    Survey.objects.create(title='existing', user=owner)
    payload = {
        'title': 'existing',
        'questions': [
            {'title': 'q1', 'question_type': 'free_text'},
            {'title': 'q2', 'question_type': 'multiple_choice', 'choices':[{'title': 'c1'}, {'title': 'c2'}]}
        ]
    }
    url = reverse('survey:list-create')
    response = api_client.post(url, data=payload, format='json')
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_create_view_allows_duplicate_title_with_different_users(user_factory, api_client):
    owner = user_factory('owner')
    another_user = user_factory('user')
    api_client.force_authenticate(owner)
    Survey.objects.create(title='existing', user=another_user)
    payload = {
        'title': 'existing',
        'questions': [
            {'title': 'q1', 'question_type': 'free_text'},
            {'title': 'q2', 'question_type': 'multiple_choice', 'choices':[{'title': 'c1'}, {'title': 'c2'}]}
        ]
    }
    url = reverse('survey:list-create')
    response = api_client.post(url, data=payload, format='json')
    
    assert response.status_code == status.HTTP_201_CREATED

#! ================================================================
#!                      SurveyDetailView
#! ================================================================

#? -------------- GET / permissions / methods ---------------

@pytest.mark.django_db
def test_detail_view_denies_anonymous_get(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)

    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_detail_view_denies_non_owner_user_get(api_client, user_factory):
    owner = user_factory('owner')
    user = user_factory('user')
    survey = Survey.objects.create(title='survey', user=owner)
    api_client.force_authenticate(user)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_detail_view_allows_owner_get(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)
    Question.objects.create(survey=survey, title='q1', question_type='free_text')
    api_client.force_authenticate(owner)
    
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data['title'] == 'survey'
    assert len(response.data['questions']) == 1

@pytest.mark.django_db
def test_detail_view_allows_superuser_get_on_other_surveys(api_client, user_factory):
    owner = user_factory('owner')
    admin = user_factory('superuser')
    admin.is_superuser = True
    admin.save()

    survey = Survey.objects.create(title='survey', user=owner)
    Question.objects.create(survey=survey, title='q1', question_type='free_text')
    api_client.force_authenticate(admin)
    
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data['title'] == 'survey'
    assert len(response.data['questions']) == 1

@pytest.mark.django_db
def test_detail_view_returns_404_for_unknown_slug(api_client, user_factory):
    owner = user_factory('owner')
    api_client.force_authenticate(owner)
    
    url = reverse('survey:detail', kwargs={'slug': 'wrong-slug'})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_detail_view_rejects_patch(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)
    api_client.force_authenticate(owner)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.patch(url, data={}, format='json')

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

#? --------------------- PUT (update) ------------------------

@pytest.mark.django_db
def test_update_view_rejects_anonymous_put(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)

    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.put(url, {}, 'json')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_update_view_rejects_non_owner_put(api_client, user_factory):
    owner = user_factory('owner')
    stranger = user_factory('stranger')
    survey = Survey.objects.create(title='survey', user=owner)

    api_client.force_authenticate(stranger)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.put(url, {}, 'json')

    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_update_view_owner_put_saves_questions_properly(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)
    q1 = Question.objects.create(title='q1', question_type='free_text', survey=survey)
    q2 = Question.objects.create(title='q2', question_type='multiple_choice', survey=survey)
    q3 = Question.objects.create(title='q3', question_type='free_text', survey=survey)
    c1 = Choice.objects.create(title='c1', question=q2)
    c2 = Choice.objects.create(title='c2', question=q2)
    c3 = Choice.objects.create(title='c3', question=q2)


    payload = {'id': survey.id, 'title': 'my survey', 'description': 'updated', 'questions': [
        #* q1 edited type and choices added
        {'id': q1.id, 'title': 'q11', 'question_type': 'multiple_choice', 'choices': [ 
            {'title': 'c1q1'}, {'title': 'c2q1'}]},
        #* q2 choices edited and one added and one deleted
        {'id': q2.id, 'title': 'q22', 'question_type': 'multiple_choice', 'choices': [
            {'id': c1.id, 'title': 'c1q2'}, {'id': c2.id, 'title': 'c2q2'}, {'title': 'c3q2'}]},
        #* q3 left out to be deleted, another q added
        {'title': 'q4', 'question_type': 'free_text'}
    ]}

    api_client.force_authenticate(owner)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.put(url, payload, 'json')

    assert response.status_code == status.HTTP_200_OK
    survey.refresh_from_db()
    assert list(survey.questions.values_list('title', flat=True)) == ['q11', 'q22', 'q4']
    assert list(survey.questions.values_list('question_type', flat=True)) == ['multiple_choice', 'multiple_choice', 'free_text']
    assert list(survey.questions.values_list('id', flat=True)) == [1, 2, 4]
    assert list(survey.questions.get(title='q11').choices.values_list('title', flat=True)) == ['c1q1', 'c2q1']
    assert list(survey.questions.get(title='q22').choices.values_list('title', flat=True)) == ['c1q2', 'c2q2', 'c3q2']

@pytest.mark.django_db
def test_update_view_success_message(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)
    q1 = Question.objects.create(title='q1', question_type='free_text', survey=survey)

    payload = {'id': survey.id, 'title': 'my survey', 'description': 'updated', 'questions': [
        {'id': q1.id, 'title': 'q11', 'question_type': 'multiple_choice', 'choices': [ 
            {'title': 'c1q1'}, {'title': 'c2q1'}]}]}
    
    api_client.force_authenticate(owner)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.put(url, payload, 'json')
    survey.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert response.data['message'] == f'Survey Updated Successfully: {survey.title}'
    assert response.data['question_count'] == 1
    assert 'detail_url' and 'response_url' in response.data

@pytest.mark.django_db
def test_update_view_freezes_questions_after_a_submission(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)
    q1 = Question.objects.create(title='q1', question_type='free_text', survey=survey)

    Submission.objects.create(survey=survey)

    payload = {'id': survey.id, 'title': 'my survey', 'description': 'updated', 'questions': [
        {'id': q1.id, 'title': 'attempted update', 'question_type': 'multiple_choice', 'choices': [ 
            {'title': 'c1q1'}, {'title': 'c2q1'}]},
        {'title': 'new q', 'question_type': 'free_text'}]}
    
    api_client.force_authenticate(owner)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.put(url, payload, 'json')
    survey.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert 'Frozen' in response.data['message']
    assert survey.questions.count() == 1
    assert survey.questions.get(title='q1').question_type == 'free_text'
    assert survey.title == 'my survey'
    assert survey.description == 'updated'

@pytest.mark.django_db
def test_update_view_rejects_duplicate_question_titles(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)
    q1 = Question.objects.create(title='q1', question_type='free_text', survey=survey)

    payload = {'id': survey.id, 'title': 'my survey', 'description': 'updated', 'questions': [
        {'id': q1.id, 'title': q1.title, 'question_type': 'multiple_choice', 'choices': [ 
            {'title': 'c1q1'}, {'title': 'c2q1'}]},
        {'title': 'q1', 'question_type': 'free_text'}]}

    api_client.force_authenticate(owner)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.put(url, payload, 'json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_update_view_rejects_duplicate_choice_titles(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)
    q1 = Question.objects.create(title='q1', question_type='free_text', survey=survey)

    payload = {'id': survey.id, 'title': 'my survey', 'description': 'updated', 'questions': [
        {'id': q1.id, 'title': q1.title, 'question_type': 'multiple_choice', 'choices': [ 
            {'title': 'c1q1'}, {'title': 'c1q1'}]},
        {'title': 'q2', 'question_type': 'free_text'}]}

    api_client.force_authenticate(owner)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.put(url, payload, 'json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_update_view_rejects_less_than_min_choice_titles(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)
    q1 = Question.objects.create(title='q1', question_type='free_text', survey=survey)

    payload = {'id': survey.id, 'title': 'my survey', 'description': 'updated', 'questions': [
        {'id': q1.id, 'title': q1.title, 'question_type': 'multiple_choice', 'choices': [ 
            {'title': 'c1q1'}]},
        {'title': 'q2', 'question_type': 'free_text'}]}

    api_client.force_authenticate(owner)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.put(url, payload, 'json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_update_view_rejects_duplicate_title_for_the_same_user(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)
    survey_2 = Survey.objects.create(title='survey-2', user=owner)
    q1 = Question.objects.create(title='q1', question_type='free_text', survey=survey)

    payload = {'id': survey.id, 'title': 'survey-2', 'description': 'updated', 'questions': [
        {'title': 'q2', 'question_type': 'free_text'}]}

    api_client.force_authenticate(owner)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.put(url, payload, 'json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST

#? ------------------------- Delete ----------------------------

@pytest.mark.django_db
def test_delete_view_rejects_anonymous_delete(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)

    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.delete(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert Survey.objects.filter(id=survey.id).exists()

@pytest.mark.django_db
def test_delete_view_rejects_non_owner_delete(api_client, user_factory):
    owner = user_factory('owner')
    stranger = user_factory('stranger')
    survey = Survey.objects.create(title='survey', user=owner)

    api_client.force_authenticate(stranger)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.delete(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Survey.objects.filter(id=survey.id).exists()

@pytest.mark.django_db
def test_delete_view_allows_owner_delete(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='survey', user=owner)

    api_client.force_authenticate(owner)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.delete(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Survey.objects.filter(id=survey.id).exists()

@pytest.mark.django_db
def test_delete_view_allows_superuser_delete(api_client, user_factory):
    owner = user_factory('owner')
    admin = user_factory('admin')
    admin.is_superuser = True
    admin.save()
    survey = Survey.objects.create(title='survey', user=owner)

    api_client.force_authenticate(admin)
    url = reverse('survey:detail', kwargs={'slug': survey.slug})
    response = api_client.delete(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Survey.objects.filter(id=survey.id).exists()

#! ================================================================
#!                      SubmissionView
#! ================================================================

#? ---------------------- GET ------------------------

@pytest.mark.django_db
def test_submission_view_get_is_public(user_factory, api_client):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='Survey', user=owner)
    Question.objects.create(survey=survey, title='q1', question_type='free_text')

    url = reverse('survey:response', kwargs={'slug': survey.slug})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data['title'] == 'Survey'
    assert len(response.data['questions']) == 1

@pytest.mark.django_db
def test_submission_view_shows_choices_for_multiple_choice_questions_only(user_factory, api_client, survey, question, ft_question, choices):
    owner = user_factory('owner')

    url = reverse('survey:response', kwargs={'slug': survey.slug})
    response = api_client.get(url)

    assert response.data['title'] == 'Base Survey'
    assert len(response.data['questions']) == 2
    assert len(response.data['questions'][0]['choices']) == 4
    assert 'choices' not in response.data['questions'][1]

@pytest.mark.django_db
def test_submission_view_get_reflects_submission_count(api_client, user_factory):
    owner = user_factory('owner')
    survey = Survey.objects.create(title='Survey', user=owner)
    Submission.objects.create(survey=survey)
    Submission.objects.create(survey=survey)

    url = reverse('survey:response', kwargs={'slug': survey.slug})
    response = api_client.get(url)

    assert response.data['total_responses'] == 2

@pytest.mark.django_db
def test_submission_view_returns_404_for_unknown_slug(user_factory, api_client, survey, question, ft_question, choices):
    url = reverse('survey:response', kwargs={'slug': 'wrong_slug'})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_404_NOT_FOUND

#? ---------------------- POST ------------------------

@pytest.mark.django_db
def test_submission_view_post_allows_anonymous_submission(api_client, user_factory, survey, question, ft_question, choices):
    owner = user_factory('owner')
    survey.user = owner
    survey.save()

    payload = {
        'answers': [
            {'question': question.id, 'chosen_choice': choices.first().id},
            {'question': ft_question.id, 'text_answer': 'hello'}
        ]
    }
    url = reverse('survey:response', kwargs={'slug': survey.slug})
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_submission_view_post_allows_authenticated_submission(api_client, user_factory, survey, question, ft_question, choices):
    owner = user_factory('owner')
    survey.user = owner
    survey.save()
    submitter = user_factory('submitter')
    api_client.force_authenticate(submitter)
    payload = {
        'answers': [
            {'question': question.id, 'chosen_choice': choices.first().id},
            {'question': ft_question.id, 'text_answer': 'hello'}
        ]
    }
    url = reverse('survey:response', kwargs={'slug': survey.slug})
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_201_CREATED
    submission = Submission.objects.filter(survey=survey).first()
    assert submission.user_id == 2

@pytest.mark.django_db
def test_submission_view_post_rejects_unanswered_required_question(api_client, user_factory, survey, question, ft_question, choices):
    owner = user_factory('owner')
    survey.user = owner
    survey.save()
    payload = {
        'answers': [
            {'question': ft_question.id, 'text_answer': 'hello'}
        ]
    }
    url = reverse('survey:response', kwargs={'slug': survey.slug})
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_submission_view_post_rejects_duplicate_submission_for_the_same_user(api_client, user_factory, survey, question, ft_question, choices):
    owner = user_factory('owner')
    survey.user = owner
    survey.save()
    submitter = user_factory('submitter')
    Submission.objects.create(survey=survey, user=submitter)
    api_client.force_authenticate(submitter)
    payload = {
        'answers': [
            {'question': question.id, 'chosen_choice': choices.first().id},
            {'question': ft_question.id, 'text_answer': 'hello'}
        ]
    }
    url = reverse('survey:response', kwargs={'slug': survey.slug})
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Submission.objects.filter(user=submitter, survey=survey).count() == 1

@pytest.mark.django_db
def test_submission_view_post_returns_404_for_unknown_slug(api_client, user_factory, survey, question, ft_question, choices):
    owner = user_factory('owner')
    survey.user = owner
    survey.save()
    payload = {
        'answers': [
            {'question': question.id, 'chosen_choice': choices.first().id},
            {'question': ft_question.id, 'text_answer': 'hello'}
        ]
    }
    url = reverse('survey:response', kwargs={'slug': 'meow'})
    response = api_client.post(url, payload, 'json')

    assert response.status_code == status.HTTP_404_NOT_FOUND

#! ================================================================
#!                       ResaultsView
#! ================================================================

@pytest.mark.django_db
def test_resaults_view_rejects_any_method_but_get(api_client, survey, user_factory):
    owner = user_factory('owner')
    survey.user = owner
    survey.save()

    url = reverse('survey:resaults', kwargs={'slug': survey.slug})
    response = api_client.post(url, {}, 'json')
    response1 = api_client.put(url, {}, 'json')
    response2 = api_client.delete(url)

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert response1.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert response2.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

@pytest.mark.django_db
def test_resaults_view_rejects_anonymous_user(api_client, survey, user_factory):
    owner = user_factory('owner')
    survey.user = owner
    survey.save()

    url = reverse('survey:resaults', kwargs={'slug': survey.slug})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_resaults_view_rejects_non_owner_user(api_client, survey, user_factory):
    owner = user_factory('owner')
    survey.user = owner
    survey.save()
    stranger = user_factory('stranger')
    api_client.force_authenticate(stranger)

    url = reverse('survey:resaults', kwargs={'slug': survey.slug})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_resaults_view_allows_owner(api_client, survey, user_factory):
    owner = user_factory('owner')
    survey.user = owner
    survey.save()
    api_client.force_authenticate(owner)

    url = reverse('survey:resaults', kwargs={'slug': survey.slug})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
def test_resaults_view_allows_superuser(api_client, survey, user_factory):
    owner = user_factory('owner')
    survey.user = owner
    survey.save()
    stranger = user_factory('stranger')
    stranger.is_superuser = True
    stranger.save()
    api_client.force_authenticate(stranger)

    url = reverse('survey:resaults', kwargs={'slug': survey.slug})
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
def test_resaults_view_return_404_on_wrong_slug(api_client, survey, user_factory):
    owner = user_factory('owner')
    survey.user = owner
    survey.save()

    url = reverse('survey:resaults', kwargs={'slug': 'meoooooow'})
    response = api_client.get(url)

    # get_object_or_404() runs before self.check_object_permissions() in the
    # view's get() - so an unknown slug is a 404 regardless of who's asking.
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_resaults_view_shows_the_whole_data_appropriately(api_client, user_factory, survey, question, ft_question, choices):
    owner = user_factory('owner')
    voter_1 = user_factory('voter_1')
    voter_2 = user_factory('voter_2')
    voter_3 = user_factory('voter_3')
    voter_4 = user_factory('voter_4')
    survey.user = owner
    survey.save()

    question_3 = Question.objects.create(survey=survey, question_type='multiple_choice', required=False)
    Choice.objects.create(question = question_3, title= 'A')
    Choice.objects.create(question = question_3, title= 'B')

    response_url = reverse('survey:response', kwargs={'slug': survey.slug})

    for voter, choice, text in [(voter_1, choices.first(), 'hello'),
                                (voter_2, choices.first(), 'meow'), 
                                (voter_3, choices.first(), '333')]:
        api_client.force_authenticate(voter)
        payload = { 'answers': [
            {'question': question.id, 'chosen_choice': choice.id},
            {'question': ft_question.id, 'text_answer': text}
        ]}
        api_client.post(response_url, payload, 'json')
    
    api_client.force_authenticate(voter_4)
    payload = { 'answers': [
        {'question': question.id, 'chosen_choice': choices.last().id},
    ]}
    api_client.post(response_url, payload, 'json')
    

    resaults_url = reverse('survey:resaults', kwargs={'slug': survey.slug})
    api_client.force_authenticate(owner)
    response = api_client.get(resaults_url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data['total_responses'] == 4
    assert len(response.data['questions']) == 3

    q1 = response.data['questions'][0]
    q2 = response.data['questions'][1]
    q3 = response.data['questions'][2]

    assert q1['times_answered'] == 4
    assert 'text_answers' not in q1
    choice_by_title = {c['title']: c for c in q1['choices']}
    assert choice_by_title['Choice 1']['times_selected'] == 3
    assert choice_by_title['Choice 1']['percentage'] == 75
    assert choice_by_title['Choice 2']['times_selected'] == 0
    assert choice_by_title['Choice 2']['percentage'] == 0
    assert choice_by_title['Choice 3']['times_selected'] == 0
    assert choice_by_title['Choice 3']['percentage'] == 0
    assert choice_by_title['Choice 4']['times_selected'] == 1
    assert choice_by_title['Choice 4']['percentage'] == 25

    assert q2['times_answered'] == 3
    assert 'choices' not in q2
    assert q2['text_answers'] == ['hello', 'meow', '333']

    assert q3['times_answered'] == 0
    choice_by_title_3 = {c['title']: c for c in q3['choices']}
    assert choice_by_title_3['A']['times_selected'] == 0
    assert choice_by_title_3['A']['percentage'] == 0 # making sure 0/0 does not happen for percentage
    assert choice_by_title_3['B']['times_selected'] == 0
    assert choice_by_title_3['B']['percentage'] == 0


