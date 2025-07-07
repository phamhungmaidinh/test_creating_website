import enum
from datetime import datetime
from flaskstarter.learning_marterial_uploader.models import LearningMaterial
from ..extensions import db 

# Using an Enum for the status makes the code cleaner and the database values consistent.
class AttemptStatus(enum.Enum):
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    ABANDONED = "Abandoned"

class Test(db.Model):
    __tablename__ = 'test'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('learning_materials.id'), nullable=False)
    
    name = db.Column(db.String(150), nullable=False)
    
    # specification of the test
    spec_scope = db.Column(db.String(255))
    spec_goal = db.Column(db.String(100))
    spec_understanding = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Establishes the one-to-many relationships. If a Test is deleted, all its Questions and Attempts are also deleted.
    questions = db.relationship('Question', back_populates='test', lazy='dynamic', cascade="all, delete-orphan")
    attempts = db.relationship('TestAttempt', back_populates='test', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Test {self.id}: {self.name}>"

class Question(db.Model):
    __tablename__ = 'question'

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, nullable=False) 

    test = db.relationship('Test', back_populates='questions')
    user_answers = db.relationship('UserAnswer', back_populates='question', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Question {self.id} (Order: {self.order}) for Test {self.test_id}>"

class TestAttempt(db.Model):
    __tablename__ = 'test_attempt'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    completed_time = db.Column(db.Integer,default = 0)

    status = db.Column(db.Enum(AttemptStatus), default=AttemptStatus.IN_PROGRESS, nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True) # Null until the test is completed
    current_question_order = db.Column(db.Integer, default=1) # will be connected with the var "order" in Question table

    test = db.relationship('Test', back_populates='attempts')
    user_answers = db.relationship('UserAnswer', back_populates='attempt', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TestAttempt {self.id} by User {self.user_id} with status {self.status}>"

class UserAnswer(db.Model):
    __tablename__ = 'user_answer'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('test_attempt.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    
    answer_text = db.Column(db.Text, nullable=False)
    feedback_text = db.Column(db.Text, nullable=True) # Null until feedback is generated
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    attempt = db.relationship('TestAttempt', back_populates='user_answers')
    question = db.relationship('Question', back_populates='user_answers')

    def __repr__(self):
        return f"<UserAnswer {self.id} for Attempt {self.attempt_id}>"