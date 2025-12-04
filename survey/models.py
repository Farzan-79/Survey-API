from django.db import models
from django.conf import settings

from .utils import slugify_instance_name
# Create your models here.


class Survey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='surveys', null=True)
    title = models.CharField(max_length=255)
    description = models.CharField(null=True, blank=True)
    slug = models.SlugField(unique=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created']
        constraints = [
            models.UniqueConstraint(
                fields=['title'],
                name= 'uniq_survey_title'
            )
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            slugify_instance_name(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Question(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    title = models.CharField(max_length=255)
    question_type = models.CharField(max_length=15, choices=[('multiple_choice', 'Multiple Choice'), ('free_text', 'Free Text')])

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['survey' ,'title'],
                name= 'uniq_question_per_survey'
            ),
        ]

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['question' ,'title'],
                name= 'uniq_choice_per_question'
            )
        ]
    

class Answer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='answers', null=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')

    # if it was multi choice:
    chosen_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True, related_name='answers')

    # if it was text:
    text_answer = models.TextField(null=True, blank=True)

    class Meta:
        #* Database-level uniqueness constraint:
        #* This creates an index/constraint so the database will refuse to insert two rows
        #* with the same (user, question). It's important to enforce this at DB level
        #* in addition to application-level checks to avoid data races and duplicates.
        constraints = [
            models.UniqueConstraint(fields=['user', 'question'], name='unique_answer')
        ]

    def __str__(self):
        return f'Answer for \"{self.question.title}\" by \"{self.user}\" : {[self.chosen_choice.title if self.chosen_choice else self.text_answer]}'
