
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length, Optional

# This is the form for CREATING the test
class TestSpecificationForm(FlaskForm):
    """Form for users to specify the details of the test they want to create."""
    name = StringField(
        'Test Name',
        validators=[InputRequired(), Length(min=3, max=150)]
    )
    # The 'choices' for these SelectFields will be populated in your view function
    scope = SelectField(
        'Scope of the Test',
        choices=[],
        validators=[InputRequired()]
    )
    goal = SelectField(
        'Primary Goal for this Test',
        choices=[
            ('Check basic comprehension', 'Check basic comprehension'),
            ('Identify my weak spots', 'Identify my weak spots'),
            ('Prepare for an exam', 'Prepare for an exam')
        ],
        validators=[InputRequired()]
    )
    understanding = SelectField(
        'Your Current Understanding',
        choices=[
            ('Just finished reading', 'Just finished reading'),
            ('Reviewed it briefly', 'Reviewed it briefly'),
            ('I feel confident', 'I feel confident')
        ],
        validators=[InputRequired()]
    )
    
    submit = SubmitField('Create Test')


# This is the form for ANSWERING a question on the test page
class AnswerForm(FlaskForm):
    answer_text = TextAreaField(
        'Your Answer',
        validators=[InputRequired(), Length(min=1, max=5000)]
    )
    submit_answer = SubmitField('Submit Answer')