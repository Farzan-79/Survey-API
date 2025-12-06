from rest_framework import serializers
from django.db import transaction
from drf_writable_nested import WritableNestedModelSerializer
import copy

from .validators import Survey_unq_validator
from .models import Survey, Question, Choice, Answer

# from rest_framework.serializers import ValidationError

#! --------------- CHOICE SERIALIZERS -------------------
class ChoiceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Choice
        fields = [
            'id',
            'title',
        ]

class ChoiceCreateSerializer(WritableNestedModelSerializer):
    class Meta:
        model = Choice
        fields = [
            'title'
        ]

#! --------------- QUESTION SERIALIZERS ------------------
class QuestionSerializer(serializers.ModelSerializer):
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
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.question_type == 'free_text':
            data.pop('choices', None)
        return data

class QuestionCreateSerializer(WritableNestedModelSerializer):
    choices = ChoiceCreateSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            'title',
            'question_type',
            'choices'
        ]
    
#! --------------- SURVEY SERIALIZERS --------------------   
class SurveyListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='survey:detail', lookup_field='slug')
    id = serializers.IntegerField(read_only=True)
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Survey
        fields = [
            'user',
            'title',
            'description',
            'id',
            'question_count',
            'url'
        ]
    def get_user(self, obj):
        return obj.user.username if obj.user else None

    def get_question_count(self, obj):
        return obj.questions.count()

class SurveyCreateSerializer(WritableNestedModelSerializer):
    questions = QuestionCreateSerializer(many=True, required=True)
    title = serializers.CharField(validators=[Survey_unq_validator])
    
    class Meta:
        model = Survey
        fields = [
            'title',
            'description',
            'questions',
        ]
    
    def to_internal_value(self, data):
        def remove_ids(value):
            #* Recursively remove 'id' from any dict or list.
            if isinstance(value, dict): #* if its a dict, pop the id
                x = value.pop('id', None)  #* remove ID if exists
                for key, val in value.items():
                    remove_ids(val)
            elif isinstance(value, list): #* if its a list, look the the dicts inside and delete their IDs if provided!
                for item in value:
                    remove_ids(item)

        data = copy.deepcopy(data)
        remove_ids(data)
        return super().to_internal_value(data)
    
    def validate(self, attrs):
        incoming_questions = attrs.get('questions')
        
        #* Validate Name Uniqueness
        q_titles = []
        for q in incoming_questions:
            qq = q.get('title')
            if qq in q_titles:
                raise serializers.ValidationError({"questions": f"Duplicate question title in this survey: '{qq}'"})
            q_titles.append(qq)

            if q.get('question_type') == 'multiple_choice':
                incoming_choices = q.get('choices', [])
                if len(incoming_choices) < 2:
                    raise serializers.ValidationError(f"A Multiple-Choice Question can't have less than 2 choices: '{qq}'")
                c_titles = []
                for c in incoming_choices:
                    cc = c.get('title')
                    if cc in c_titles:
                        raise serializers.ValidationError({"choices": f"Duplicate choice in question '{qq}': '{cc}'"})
                    c_titles.append(cc)

            elif q.get('question_type') == 'free_text':
                if q.get('choices'):
                    raise serializers.ValidationError(f"A Free-Text Question Can't accept Choices: '{qq}'")
        return attrs

class SurveyDetailSerializer(serializers.ModelSerializer):
    #? Handles Update, Retrieve, and Delete

    questions = QuestionSerializer(many=True)
    user = serializers.CharField(read_only=True)
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(validators=[Survey_unq_validator])


    class Meta:
        model = Survey
        fields = [
            'id',
            'user',
            'title',
            'description',
            'questions',
        ]

    def validate(self, attrs):
        #? Bulk-validate ownership of incoming question and choice IDs:
        #? - every incoming question id must belong to this survey
        #? - every incoming choice id must belong to the question it was declared under
        #? This runs once and uses bulk queries, avoiding N DB hits.
        #? we only check those with IDs, those without IDs are going to be created and have no need of validating

        instance = getattr(self, 'instance', None)
        if not instance:
            #* survey not provided, this serializer does not handle create
            return serializers.ValidationError("Survey Not Found", code=404)
        
        incoming_questions = attrs.get('questions')
        if not incoming_questions:
            #* no questions to update, 
            return attrs
        
        #? Validate Name Uniqueness and counts
        q_titles = []
        for q in incoming_questions:
            qq = q.get('title')
            if qq in q_titles:
                raise serializers.ValidationError({"questions": f"Duplicate question title in this survey: '{qq}'"})
            q_titles.append(qq)

            if q.get('question_type') == 'multiple_choice':
                incoming_choices = q.get('choices', [])
                if len(incoming_choices) < 2:
                    raise serializers.ValidationError(f"A Multiple-Choice Question can't have less than 2 choices: '{qq}'")
                c_titles = []
                for c in incoming_choices:
                    cc = c.get('title')
                    if cc in c_titles:
                        raise serializers.ValidationError({"choices": f"Duplicate choice in question '{qq}': '{cc}'"})
                    c_titles.append(cc)

            elif q.get('question_type') == 'free_text':
                if q.get('choices'):
                    raise serializers.ValidationError(f"A Free-Text Question Can't accept Choices: '{qq}'")

        
        #? VALIDATING OWNERSHIP
        incoming_q_ids = set() #* a set of all the incoming question with IDs
        incoming_declared_choice_to_question = {} #* a dict of choice IDs as keys, and their declared questions IDs and their value
        #* collecting the above vars:
        for q in incoming_questions: 
            qid = q.get('id')
            if qid:
                incoming_q_ids.add(qid)
            for c in q.get('choices', []) or []:
                cid = c.get('id')
                if cid is not None and qid is not None:
                    incoming_declared_choice_to_question[cid] = qid
                elif cid is not None and qid is None:
                    #* client supplies a choice id but not the parent question id: ambiguous
                    raise serializers.ValidationError({
                        "questions": 
                            "When sending existing choice.id you must also provide the parent question id."})
        
        #? Validate question ownership in bulk:
        if incoming_q_ids:
            #* checking if the incoming ids are in DB:
            question_qs = Question.objects.filter(id__in=incoming_q_ids).only('id', 'survey_id')
            db_q_ids = set(q.id for q in question_qs)
            missing_question_ids = incoming_q_ids - db_q_ids
            if missing_question_ids:
                raise serializers.ValidationError({'questions': f'Question IDs not found: {sorted(missing_question_ids)}'})
            
            #* ensure all those questions belong to this survey
            wrong_question = [q.id for q in question_qs if q.survey_id != instance.id]
            if wrong_question:
                raise serializers.ValidationError({'questions': f'Question IDs do not belong to this survey: {sorted(wrong_question)}'})
        
        #? Validate Choice ownership in bulk
        if incoming_declared_choice_to_question:
            #* checking if the incoming ids are in DB:
            incoming_c_ids = list(incoming_declared_choice_to_question.keys())
            choice_qs = Choice.objects.filter(id__in=incoming_c_ids).only('id', 'question_id')
            db_c_ids = set(c.id for c in choice_qs)
            missing_choice_ids = set(incoming_c_ids) - db_c_ids
            if missing_choice_ids:
                raise serializers.ValidationError({'questions': f'Choice ids not found: {sorted(missing_choice_ids)}'})
            
            #* check that each declared choice belongs to the declared question
            mismatch = []
            for c in choice_qs:
                declared_parent_q_id = incoming_declared_choice_to_question.get(c.id)
                if c.question_id != declared_parent_q_id:
                    mismatch.append({'choice_id': c.id, 'actual_question_id': c.question_id, 'declared_question_id': declared_parent_q_id})
            if mismatch:
                raise serializers.ValidationError({'questions': 'Some choice ids do not belong to the declared question', 'details': mismatch})
    
        return attrs
    
    @transaction.atomic
    def update(self, instance: Survey, validated_data):
        #? Deterministic PUT semantics:
        #?   - Update survey fields
        #?   - For questions: update if id provided and belongs to this survey; create otherwise
        #?   - Remove DB questions not present in incoming list (replace semantics)
        #?   - For each question handle choices similarly (update/create/delete)

        #* popping the question data out to handle later
        question_data = validated_data.pop('questions', None)

        #* Update survey base fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if not question_data:
            raise serializers.ValidationError({"Survey": "A Survey must have at least one Question"})
        

        existing_questions = list(instance.questions.all().only('id')) #* list of all existing question objects in this survey
        existing_questions_dict = {q.id: q for q in existing_questions} #* dict of question.id --> question object
        question_to_keep = set() #* a set of IDs of questions to keep

        for q_data in question_data:
            q_id = q_data.get('id', None)

            #* popping out choice data to handle later
            choice_data = q_data.pop('choices', []) or None

            if q_id is not None: 
                #* question exists, and we validated it before, so UPDATE
                q_obj = existing_questions_dict.get(q_id)

                for attr, value in q_data.items():
                    setattr(q_obj, attr, value)
                q_obj.save()
                question_to_keep.add(q_obj.id)

            else: 
                #* create a new question
                q_obj = Question.objects.create(survey=instance, **q_data)
                question_to_keep.add(q_obj.id)

            if not choice_data:
                #* no nested choices, go to the next question
                continue

            existing_choices = list(q_obj.choices.all().only('id')) #* list of all existing choices objects in this question
            existing_choices_dict = {c.id: c for c in existing_choices} #* dict of choice.id --> choice object
            choices_to_keep = set() #* a set of IDs of questions to keep

            for c_data in choice_data:
                c_id = c_data.get('id', None)

                
                if c_id is not None:
                    #* the choice id exists, and is validated before, UPDATE
                    c_obj = existing_choices_dict.get(c_id)

                    for attr, value in c_data.items():
                        setattr(c_obj, attr, value)
                    c_obj.save()
                    choices_to_keep.add(c_obj.id)
                
            
                else:
                    #* create new choice
                    c_obj = Choice.objects.create(question=q_obj, **c_data)
                    choices_to_keep.add(c_obj.id)
                
            choices_to_delete = set(existing_choices_dict.keys()) - choices_to_keep
            if choices_to_delete:
                Choice.objects.filter(id__in=choices_to_delete).delete()

        questions_to_delete = set(existing_questions_dict.keys()) - question_to_keep
        if questions_to_delete:
            Question.objects.filter(id__in=questions_to_delete).delete()

        return instance



        







