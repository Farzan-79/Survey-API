from rest_framework import serializers
from .models import Survey, Question, Choice, Answer
from drf_writable_nested import WritableNestedModelSerializer
# from rest_framework.serializers import ValidationError

class ChoiceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Choice
        fields = [
            'id',
            'title',
        ]

    def validate(self, attrs):

        #?  - self.parent is the ListSerializer (choices list)
        #?  - self.parent.parent is the QuestionSerializer instance
        print(attrs)
        print(f'-----{self.context}')

        incoming_choice_id = attrs.get('id', None)

        if not incoming_choice_id:
            return attrs
        
        else:
            try:
                existing_choice = Choice.objects.only('id', 'question_id').get(id=incoming_choice_id)
            except Choice.DoesNotExist:
                raise serializers.ValidationError('Choice object with provided ID was not found')


            existing_parent_q_id = existing_choice.question_id
            print(f'Existing Parent Question ID: {existing_parent_q_id}')

            print(f'--------{self.parent}')
            ser_parent_q = getattr(self.parent.parent, "instance", None)
            print(f'Serializer Parent Question ID: {ser_parent_q}')

            if existing_parent_q_id != ser_parent_q.id:
                raise serializers.ValidationError('this Choice does not belong to the Question')
            
            return attrs
            

class QuestionSerializer(WritableNestedModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)
    id = serializers.IntegerField(required=False)


    class Meta:
        model = Question
        fields = [
            'id',
            'title',
            'question_type',
            'choices'
        ]
    


    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        if instance:
            parent_survey = self.context.get('survey')
            if instance.survey_id != parent_survey.id:
                raise serializers.ValidationError("The Question does not belong to this Survey")
        return attrs
    


class SurveyCreateSerializer(WritableNestedModelSerializer):
    questions = QuestionSerializer(many=True, required=False)

    class Meta:
        model = Survey
        fields = [
            'title',
            'description',
            'questions',
        ]

    # def create(self, validated_data):
    #     question_data = validated_data.pop('questions')
        
    #     request = self.context.get('request')

    #     user = request.user if request.user.is_authenticated else None
    #     survey = Survey.objects.create(user=user, **validated_data)

    #     if question_data:
    #         for qdata in question_data:
    #             choice_data = qdata.pop('choices')
    #             question = Question.objects.create(survey=survey, **qdata)
    
    #             if choice_data:
    #                 for cdata in choice_data:
    #                     Choice.objects.create(question=question, **cdata)
    #     return survey
    
class SurveyListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='survey:detail', lookup_field='slug')
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Survey
        fields = [
            'title',
            'description',
            'id',
            'question_count',
            'url'
        ]
    
    def get_question_count(self, obj):
        return obj.questions.count()
    
class SurveyDetailSerializer(WritableNestedModelSerializer):
    questions = QuestionSerializer(many=True)
    user = serializers.CharField(read_only=True)
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Survey
        fields = [
            'id',
            'user',
            'title',
            'description',
            'questions',
        ]
    
    # def get_fields(self):
    #     fields = super().get_fields()
    #     fields['questions'].child.context.update({"survey":self.instance})
    #     print(fields['questions'].child.context)
    #     return fields





