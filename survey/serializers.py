from rest_framework import serializers
from .models import Survey, Question, Choice, Answer

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = [
            'id',
            'title'
        ]

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)
    class Meta:
        model = Question
        fields = [
            'id',
            'title',
            'question_type',
            'choices'
        ]

class SurveySerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, required=False)

    class Meta:
        model = Survey
        fields = [
            'id',
            'title',
            'description',
            'questions',
        ]

    def create(self, validated_data):
        question_data = validated_data.pop('questions')
        
        survey = Survey.objects.create(**validated_data)

        try:
            user = self.request.user if self.request.user.is_authenticated else None
        except:
            user = None

        for qdata in question_data:
            choice_data = qdata.pop('choices')
            question = Question.objects.create(survey=survey, **qdata)

            if choice_data:
                for cdata in choice_data:
                    Choice.objects.create(question=question, **cdata)
        
        return survey