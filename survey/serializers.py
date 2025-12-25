from rest_framework import serializers
from django.db import transaction
from drf_writable_nested import WritableNestedModelSerializer
from rest_framework.serializers import ValidationError

from .validators import Survey_unq_validator
from .models import Survey, Question, Choice, Answer, Submission


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
    required = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Question
        fields = [
            'id',
            'title',
            'question_type',
            'required',
            'choices',
        ]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.question_type == 'free_text':
            data.pop('choices', None)
        elif instance.question_type == 'free_text':
            data.pop('multiple_choice', None)
        return data

class QuestionCreateSerializer(WritableNestedModelSerializer):
    choices = ChoiceCreateSerializer(many=True, required=False)
    required = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = Question
        fields = [
            'title',
            'question_type',
            'required',
            'choices'
        ]
    
#! --------------- SURVEY SERIALIZERS --------------------   
class SurveyListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name='survey:detail', lookup_field='slug')
    id = serializers.IntegerField(read_only=True)
    total_responses = serializers.SerializerMethodField(read_only=True)
    user = serializers.SerializerMethodField(read_only= True)

    class Meta:
        model = Survey
        fields = [
            'title',
            'user',
            'id',
            'question_count',
            'total_responses',
            'url'
        ]

    def get_user(self, obj):
        return obj.user.username if obj.user else None

    def get_total_responses(self, obj):
        return obj.submission_count

    def get_question_count(self, obj):
        return obj.question_count
        
    def get_fields(self):
        fields = super().get_fields()
        if not self.context.get('request').user.is_superuser:
            fields.pop('user')
        return fields

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

        #data = copy.deepcopy(data)
        remove_ids(data)
        return super().to_internal_value(data)
    
    def validate(self, attrs):
        incoming_questions = attrs.get('questions')
        
        #* Validate Name Uniqueness
        q_titles = []
        for q in incoming_questions:
            qq = q.get('title')
            if qq in q_titles:
                raise ValidationError({"questions": f"Duplicate question title in this survey: '{qq}'"})
            q_titles.append(qq)

            if q.get('question_type') == 'multiple_choice':
                incoming_choices = q.get('choices', [])
                if len(incoming_choices) < 2:
                    raise ValidationError(f"A Multiple-Choice Question can't have less than 2 choices: '{qq}'")
                c_titles = []
                for c in incoming_choices:
                    cc = c.get('title')
                    if cc in c_titles:
                        raise ValidationError({"choices": f"Duplicate choice in question '{qq}': '{cc}'"})
                    c_titles.append(cc)

            elif q.get('question_type') == 'free_text':
                if q.get('choices'):
                    raise ValidationError(f"A Free-Text Question Can't accept Choices: '{qq}'")
        return attrs

class SurveyCreatedMessageSerializer(serializers.ModelSerializer):
    detail_url = serializers.HyperlinkedIdentityField(view_name= 'survey:detail', lookup_field='slug')
    response_url = serializers.HyperlinkedIdentityField(view_name= 'survey:response', lookup_field= 'slug')
    question_count = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()

    class Meta:
        model = Survey
        fields= [
            'message',
            'question_count',
            'detail_url',
            'response_url'
        ]

    def get_message(self, obj):
        return f'Your Survey has been saved successfuly: {obj.title}'

    def get_question_count(self, obj):
        return self.context.get('question_count')

class SurveyDetailSerializer(serializers.ModelSerializer):
    #? Handles Update, Retrieve, and Delete
    questions = QuestionSerializer(many=True)
    user = serializers.CharField(read_only=True)
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(validators=[Survey_unq_validator])
    response_url = serializers.HyperlinkedIdentityField(view_name= 'survey:response', lookup_field='slug')
    resaults_url = serializers.HyperlinkedIdentityField(view_name= 'survey:resaults', lookup_field='slug')
    total_responses = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Survey
        fields = [
            'id',
            'user',
            'title',
            'description',
            'questions',
            'total_responses',
            'response_url',
            'resaults_url'
        ]

    def get_total_responses(self, obj):
        return getattr(obj, "submission_count", obj.submissions.count())

    def validate(self, attrs):
        """
        Bulk-validate nested update payload.

        Goals:
        - validate local payload consistency (duplicate titles, min choices, etc.)
        - validate ownership of IDs (question.id belongs to this survey, choice.id belongs to declared question)
        - do it with NO N+1 queries (ideally 0 extra queries if prefetched objects exist)
        """

        instance = getattr(self, 'instance', None)
        if not instance:
            raise ValidationError("Survey Not Found", code=404)
        
        #* if there is a submission on this survey, it must be frozen and the questions can't change
        submission_count = getattr(instance, "submission_count", instance.submissions.count())
        self._frozen = False
        if submission_count > 0:
            if 'questions' in attrs:
                attrs.pop('questions', None)
                self._frozen = True
            return attrs
        
        incoming_questions = attrs.get('questions')
        if not incoming_questions:
            raise ValidationError({"Survey": "A Survey must have at least one Question"})


        #? ---------------------------------------------------------------------
        #? 1) Payload-only validation (doesn't touch DB)
        #? ---------------------------------------------------------------------
        q_titles = []
        for q in incoming_questions:
            qq = q.get('title')
            if qq in q_titles:
                raise ValidationError({"questions": f"Duplicate question title in this survey: '{qq}'"})
            q_titles.append(qq)

            if q.get('question_type') == 'multiple_choice':
                incoming_choices = q.get('choices', [])
                if len(incoming_choices) < 2:
                    raise ValidationError(f"A Multiple-Choice Question can't have less than 2 choices: '{qq}'")

                c_titles = []
                for c in incoming_choices:
                    cc = c.get('title')
                    if cc in c_titles:
                        raise ValidationError({"choices": f"Duplicate choice in question '{qq}': '{cc}'"})
                    c_titles.append(cc)

            elif q.get('question_type') == 'free_text':
                if q.get('choices'):
                    raise ValidationError(f"A Free-Text Question can't accept choices: '{qq}'")


        #? ---------------------------------------------------------------------
        #? 2) Collect incoming IDs (still no DB)
        #? ---------------------------------------------------------------------
        incoming_q_ids = set()  #* question IDs provided by client
        incoming_choice_to_question = {}  #* choice_id -> declared_question_id

        for q in incoming_questions:
            qid = q.get('id')
            if qid:
                incoming_q_ids.add(qid)

            for c in (q.get('choices') or []):
                cid = c.get('id')
                if cid is not None and qid is not None:
                    #* client says: this existing choice belongs under this existing question
                    if incoming_choice_to_question.get(cid):
                        #* if a choice has already been added to the incoming dict, dont change it.
                        continue
                    incoming_choice_to_question[cid] = qid
                elif cid is not None and qid is None:
                    #* client gave choice.id but didn't tell us which existing question it belongs to
                    raise ValidationError({
                        "questions": "When sending existing choice.id you must also provide the parent question id."
                    })


        #? ---------------------------------------------------------------------
        #? 3) Get existing questions/choices in-memory (NO DB if prefetched exists)
        #? ---------------------------------------------------------------------
        #* the view uses:
        #* Prefetch('questions', queryset=Question.objects.prefetch_related('choices'), to_attr='prefetched_questions')
        #* So instance.prefetched_questions should be a Python list already loaded.
        existing_question_qs = getattr(instance, 'prefetched_questions', None)

        #* If someone calls this serializer without that view/queryset, fallback safely.
        #* (This fallback WILL query, but it prevents crashing.)
        if existing_question_qs is None:
            existing_question_qs = list(
                instance.questions.all().prefetch_related('choices')
            )

        existing_q_ids = {q.id for q in existing_question_qs}


        #? ---------------------------------------------------------------------
        #? 4) Validate incoming question ids belong to this survey (no DB)
        #? ---------------------------------------------------------------------
        if incoming_q_ids:
            invalid_q_ids = incoming_q_ids - existing_q_ids
            if invalid_q_ids:
                raise ValidationError({
                    'questions': f'Invalid question ids for this survey: {sorted(invalid_q_ids)}'
                })


        #? ---------------------------------------------------------------------
        #? 5) Validate incoming choice ids + ownership (no DB)
        #? ---------------------------------------------------------------------
        if incoming_choice_to_question:
            #* Build a map: existing choice_id -> actual parent question_id
            #* This uses prefetched choices, so it does NOT hit the DB.
            existing_choice_to_quesiton = {}
            for q in existing_question_qs:
                for c in q.choices.all():  #* uses prefetch cache
                    existing_choice_to_quesiton[c.id] = q.id

            incoming_c_ids = set(incoming_choice_to_question.keys())

            #* 5a) Do all incoming choice IDs exist inside THIS survey?
            invalid_choice_ids = incoming_c_ids - set(existing_choice_to_quesiton.keys())
            if invalid_choice_ids:
                raise ValidationError({
                    'choices': f'Invalid choice ids for this survey: {sorted(invalid_choice_ids)}'
                })

            print(f'incoming: {incoming_choice_to_question}')
            print(f'existing: {existing_choice_to_quesiton}')
            #* 5b) Does each choice belong to the declared question?
            mismatch = []
            for cid, declared_qid in incoming_choice_to_question.items():
                actual_qid = existing_choice_to_quesiton.get(cid)
                if actual_qid != declared_qid:
                    mismatch.append({
                        'choice_id': cid,
                        'actual_question_id': actual_qid,
                        'declared_question_id': declared_qid
                    })

            if mismatch:
                raise ValidationError({
                    'choices': 'Some choice ids do not belong to the declared question.',
                    'details': mismatch
                })

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

        #* Update survey fields (optional micro-opt: update_fields)
        changed = False
        for attr, value in validated_data.items():
            if getattr(instance, attr) != value:
                setattr(instance, attr, value)
                changed = True
        if changed:
            instance.save()

        submission_count = getattr(instance, "submission_count", instance.submissions.count())
        if self._frozen:
            return instance
        
        existing_questions = list(getattr(instance, "prefetched_questions", instance.questions.all())) #* list of all existing question objects in this survey, if the prefetched data does not exist, fallback to db
        existing_questions_dict = {q.id: q for q in existing_questions} #* dict of question.id --> question object
        question_to_keep = set() #* a set of IDs of questions to keep

        for q_data in question_data:
            q_id = q_data.get('id', None)

            #* popping out choice data to handle later
            choice_data = q_data.pop('choices', []) or None

            if q_id is not None: 
                #* question exists, and we validated it before, so: UPDATE if changed
                q_obj = existing_questions_dict[q_id]
                q_changed = False
                for attr, value in q_data.items():
                    if getattr(q_obj, attr) != value:
                        setattr(q_obj, attr, value)
                        q_changed = True
                if q_changed:
                    q_obj.save()
                question_to_keep.add(q_obj.id)
            else: 
                #* create a new question
                q_obj = Question.objects.create(survey=instance, **q_data)
                question_to_keep.add(q_obj.id)

            if not choice_data:
                #* no nested choices, go to the next question
                continue

            existing_choices = list(q_obj.choices.all()) if q_id else [] #* list of all existing choices objects in this question
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

#*------------- PARTIAL DETAIL SERIALIZERS --------------
class SurveyDetailWriteSerializer(SurveyDetailSerializer):
    questions = QuestionSerializer(many=True)

class SurveyDetailReadSerializer(SurveyDetailSerializer):
    questions = serializers.SerializerMethodField()

    def get_questions(self, obj):
        qs= obj.prefetched_questions
        return QuestionSerializer(qs, many=True, context=self.context).data
#* ------------------------------------------------------

class SurveyUpdateMessageSerializer(serializers.ModelSerializer):
    detail_url = serializers.HyperlinkedIdentityField(view_name= 'survey:detail', lookup_field= 'slug')
    response_url = serializers.HyperlinkedIdentityField(view_name= 'survey:response', lookup_field= 'slug')
    message = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()

    class Meta:
        model= Survey
        fields= [
            'message',
            'question_count',
            'detail_url',
            'response_url',
        ]
    
    def get_message(self, obj):
        if self.context.get('frozen'):
            return f'This Survey is frozen because it has already been answered: {obj.title} \n Only the title and Description were updated'
        return f'Survey Updated Successfully: {obj.title}'
    
    def get_question_count(self, obj):
        return self.context.get('question_count') or obj.questions.count()

#! --------------- ANSWER SERIALIZERS --------------------
class AnswerSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(queryset= Question.objects.none())
    chosen_choice = serializers.PrimaryKeyRelatedField(queryset= Choice.objects.none(),
                                                       allow_null= True,
                                                       required= False,)
    

    class Meta:
        model = Answer
        fields= [
            'question',
            'chosen_choice',
            'text_answer'
        ]
        extra_kwargs = { #* this is the same thing as declaring a field in the top, but here we are just changing its kwargs
            'text_answer' : {'allow_null':True, 'required': False, 'allow_blank': True}
        }

    def __init__(self, instance=None, data=..., **kwargs):
        x = super().__init__(instance, data, **kwargs)
        survey = self.context.get('survey')
        if survey:
            self.fields['question'].queryset = survey.questions.all()
            self.fields['chosen_choice'].queryset = Choice.objects.filter(question__survey= survey)

    
    def validate(self, attrs):
        survey = self.context.get('survey', None)
        question = attrs.get('question')
        chosen_choice = attrs.get('chosen_choice')
        text_answer = attrs.get('text_answer')


        if not question:
            raise ValidationError({'question': 'Question is required.'})
        
        if question.survey_id != survey.id:
            raise ValidationError({'question': 'This Question does not belong to this Survey'})
        
        if question.question_type == 'multiple_choice':
            if not chosen_choice:
                raise ValidationError({'chosen_choice': 'This field is required for multiple choice questions.'})
            if text_answer:
                raise ValidationError({'text_answer': 'Multiple choice questions cannot have text answers.'})
            if chosen_choice.question_id != question.id:
                raise ValidationError({'chosen_choice': 'This choice does not belong to the selected question.'})
            
        elif question.question_type == 'free_text':
            if not text_answer:
                raise ValidationError({'text_answer': 'This field is required for free text questions.'})
            if chosen_choice:
                raise ValidationError({'chosen_choice': 'Free Text questions cannot have choices.'})
            
        else:
            raise ValidationError({'question': f'Unsupported question_type: {question.question_type}'})
        
        


        return attrs
    
class SubmissionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True)

    class Meta:
        model = Submission
        fields = [
            'answers',
            'user'
        ]
        read_only_fields = ['id', 'created']

    def get_fields(self):
        fields = super().get_fields()
        fields['answers'] = AnswerSerializer(many=True,
                                             context={
                                                 'survey': self.context.get('survey'),
                                                 'request': self.context.get('request')
                                             })
        return fields

    def validate(self, attrs):
        survey = self.context.get('survey')
        answers = attrs['answers']

        required_questions = set(survey.questions.filter(required=True).values_list('id', flat=True))
        answered_questions = {a.get('question').id for a in answers}

        missing_questions = required_questions - answered_questions
        if len(missing_questions) > 0:
             raise ValidationError({"required_questions": 
                                        {'id': list(missing_questions)}
                                    })

        if len(answered_questions) != len(answers): #* missing questions is a set, and duplicates are deleted
            raise ValidationError("Duplicate answers for the same question are not allowed.")       
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        answers= validated_data.pop('answers')
        survey = self.context.get('survey')
        request = self.context.get('request')

        user = request.user if(request and request.user.is_authenticated) else None

        if user and user.is_authenticated:
            if Submission.objects.filter(user=user, survey=survey).exists():
                raise serializers.ValidationError(
                    f'{user.username}, You have already answered this question.'
                )
            
        submission = Submission.objects.create(survey=survey, user=user)

        for answer in answers:
            Answer.objects.create(submission=submission, **answer)

        return submission

#! --------------- RESAULT SERIALZERS --------------------
class ChoiceResaultSerializer(serializers.ModelSerializer):
    times_selected = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()


    class Meta:
        model = Choice
        fields = [
            'title',
            'times_selected',
            'percentage'
        ]
    
    def get_times_selected(self, obj):
        return obj.times_selected
    
    def get_percentage(self, obj):
        total = self.context.get('times_answered_question')
        if total == 0:
            return 0
        return round((obj.times_selected / total) * 100, 2)

class QuestionResaultSerializer(serializers.ModelSerializer):
    choices = serializers.SerializerMethodField()
    times_answered = serializers.SerializerMethodField(read_only=True)
    text_answers = serializers.SerializerMethodField() 

    class Meta:
        model = Question
        fields = [
            'id',
            'title',
            'question_type',
            'required',
            'times_answered',
            'choices',
            'text_answers'
        ]

    def get_choices(self, obj):
        return ChoiceResaultSerializer(
            obj.prefetched_choices,
            many=True,
            context={'times_answered_question': obj.times_answered}
        ).data
    
    def get_text_answers(self, obj):
        if obj.question_type != 'free_text':
            return None
        return [A.text_answer for A in obj.prefetched_text_answers]

    def get_times_answered(self, obj):
        return obj.times_answered
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.question_type == 'multiple_choice':
            data.pop('text_answers', None)
        elif instance.question_type == 'free_text':
            data.pop('choices', None)
        return data
    
class SurveyResaultSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    total_responses = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model= Survey
        fields = [
            'id',
            'title',
            'description',
            'total_responses',
            'questions'
        ]
    
    def get_questions(self, obj):
        return QuestionResaultSerializer(
            obj.prefetched_questions,
            many=True
        ).data

    def get_total_responses(self, obj):
        return obj.times_submitted       



        







