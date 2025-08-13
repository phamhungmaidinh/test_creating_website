
from flask import (render_template, redirect,url_for,request,flash,current_app,Blueprint)
from flask_login import login_required, current_user
from .forms import TestSpecificationForm, AnswerForm
from .models import Test,Question,TestAttempt,UserAnswer,LearningMaterial
import json
import google.generativeai as genai
from ..extensions import db
from flaskstarter.utils import request_ai


test_learning_function_bp = Blueprint(
    'test_learning_function_bp',
    __name__,
    template_folder='templates',
    url_prefix='/test_learning_function'
)

    
def call_AI_for_test_generation(scope_of_test, goal_of_test, current_understanding, roadmap=None, material=None):
    prompt = f"""
            **Role:**
            You are an expert educator and instructional designer. Your task is to create a high-quality, open-ended test based on a student's learning goals and the provided material.

            **Context:**
            - **Roadmap (if available):** {roadmap}
            - **Source Material / Text:** ---
            {material}
            ---
            - **Student's Specifications:**
            - **Scope of the test:** "{scope_of_test}"
            - **Student's current understanding:** "{current_understanding}"
            - **Student's primary goal for this test:** "{goal_of_test}"

            **Task:**
            You must perform the following two steps in order:

            1.  **Determine Question Count:** First, you **MUST** analyze all the provided context (the material, the scope, and the user's goal) to calculate the single most appropriate number of questions for a test. A basic goal requires fewer questions than an exam preparation goal.

            2.  **Generate Test Questions:** Generate the exact number of open-ended questions you determined in Step 1. The questions must be tailored to the student's goal and be based only on the provided material within the specified scope.

            **Format and Constraints:**
            1.  The entire output **MUST** be a single, valid JSON object.
            2.  The JSON object **MUST** contain two top-level keys:
                - `"generated_question_count"`: The integer for the number of questions you decided to create.
                - `"questions"`: A list of strings, where each string is a unique question.
            3.  **DO NOT** add any text, explanations, or remarks outside the JSON structure.

            **Example of your required output:**
            ```json
            {{
            "generated_question_count": 8,
            "questions": [
                "First question...?",
                "Second question...?",
                "Third question...?",
                "Fourth question...?",
                "Fifth question...?",
                "Sixth question...?",
                "Seventh question...?",
                "Eighth question...?"
            ]
            }}
            """
    return prompt

def create_feedback_prompt(question_text, current_user_answer, conversation_history):
    prompt = f"""
        **Role:**
        You are an expert, encouraging Socratic tutor. Your goal is to guide the student towards the correct answer without simply giving it away.

        **Context:**
        - **The original question is:** "{question_text}"
        - **The student's current answer is:** "{current_user_answer}"
        - **Previous answer of this user on this question (if any):**
        ---
        {conversation_history}
        ---

        **Task:**
        Analyze the student's **current answer** in the context of the question and the **previous conversation history**.
        1.  If the student has improved on a previous answer, acknowledge their progress.
        2.  If the current answer is correct, praise them and confirm their understanding.
        3.  If the current answer is still incorrect or incomplete, **do not give the direct answer**. Instead, ask a guiding question or provide a small hint that builds on your previous feedback to help them think about the topic in a new way.

        **Format and Constraints:**
        - The output MUST be a single, valid JSON object.
        - The JSON object MUST contain one top-level key: "feedback_text".
        - Keep the feedback concise, encouraging, and focused on guiding the student.

        **Example of your required output:**
        ```json
        {{
        "feedback_text": "That's a much better attempt! You're now correctly identifying that Aristotle saw procrastination as a problem of habit. To take it one step further, can you recall what he believed was the primary source of that bad habit?"
        }}
        """
    return prompt



#ROUTE 1 for creating a new test
@test_learning_function_bp.route('/create_test', methods = ['GET','POST'])
@login_required
def create_test():
    # choosing the material for the test
    # Query the database for all materials owned by the current user
    test_spec = TestSpecificationForm()
    user_materials = LearningMaterial.query.filter_by(user_id=current_user.id).all()
    test_spec.material_id.choices = [(m.id, m.title) for m in user_materials]
    #displaying the form ,that needed to be filled in to create a test.
    #if the choosing method is from the old test automatically just fill out all the form.Other case the blank space will be displayed.
    if request.method == 'GET':
    #displaying the choosing page
        return render_template(
        'test_learning_function/creating_test.html',
        page_title='Creating Test',
        test_spec1=test_spec,
        materials = user_materials 
        )
    else:
        if test_spec.validate_on_submit(): #bug here
                selected_id =test_spec.material_id.data
                material = LearningMaterial.query.get(selected_id)
                input_file = None
                prompt = ""
                if material.gemini_file_uri : # to check if that is a file
                    input_file = genai.get_file(name = material.gemini_file_uri)
                    prompt = call_AI_for_test_generation(
                        test_spec.scope.data,
                        test_spec.understanding.data,
                        test_spec.goal.data,
                        material.analysis_roadmap
                        )
                    
                    test_text= request_ai(prompt,input_file)
                    flash(f"Success bro")
                else:
                    #link case where the exatracted text = material
                    extracted_text = material.analysis_roadmap
                    prompt = call_AI_for_test_generation(
                        test_spec.scope.data,
                        test_spec.understanding.data,
                        test_spec.goal.data,
                        None,
                        extracted_text
                        )
                    test_text = request_ai(prompt)
            #updating the database didnt if this right or wrong
            #update fucking 4 table :))))
                if test_text and 'questions' in test_text:
                    try:
                        new_test = Test(
                            name = test_spec.name.data,
                            user_id = current_user.id,
                            material_id = material.id,
                            spec_scope = test_spec.scope.data,
                            spec_goal = test_spec.goal.data,
                            spec_understanding = test_spec.understanding.data,
                        )
                        db.session.add(new_test)
                        #2. Loop through the questions from the AI and create Question objects
                        for i, q_text in enumerate(test_text['questions']):
                            question = Question(
                                question_text=q_text,
                                order=i + 1,  # Set the question order (1, 2, 3...)
                                test=new_test  # Link this question to the new test
                            )
                            db.session.add(question)
                        # 3. Create the first 'TestAttempt' so the user can start the test right away
                        new_attempt = TestAttempt(
                            user_id=current_user.id, # Link the attempt to the user
                            test=new_test      # Link the attempt to the new test
                        )
                        db.session.add(new_attempt)

                        # 4. Commit all the new objects to the database in one transaction
                        db.session.commit()

                        flash(f"Success! Your test '{new_test.name}' has been created.", 'success')
                    
                    # 5. Redirect the user to the test-taking page for their new attempt
                    #Need to fix from here redirect to the test_storage function
                        return redirect(url_for('test_learning_function_bp.take_test', test_attempt_id=new_attempt.id))

                    except Exception as e:
                        db.session.rollback() # Undo changes if an error occurs
                        flash(f"A database error occurred: {e}", "danger")
                        return render_template(
                            'test_learning_function/creating_test.html',
                            page_title='Creating Test',
                            test_spec1=test_spec,
                            materials = user_materials 
                            )
        else:
            flash (f"Fucking you the page still have bugs")
            return render_template(
                'test_learning_function/creating_test.html',
                page_title='Creating Test',
                test_spec1=test_spec,
                materials = user_materials 
                )
    #return redirect(url_for('test_learning_function_bp.take_test', test_attempt_id=new_attempt.id))

        
@test_learning_function_bp.route('/take_test/<int:test_attempt_id>', methods = ['GET','POST'])
@login_required

def take_test(test_attempt_id):
    attempt
            
        


            





