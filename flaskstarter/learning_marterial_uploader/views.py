import os
import json
import uuid  # For generating unique filenames
from flask import (render_template, redirect, url_for, request, flash,
                   current_app,Blueprint)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .forms import FileUploadForm, LinkSubmitForm
from .models import LearningMaterial #importing tabel/database for this feature
from ..extensions import db  
import google.generativeai as genai
from flaskstarter.utils import request_ai,get_content

learning_material_uploader_bp = Blueprint(
    'learning_material_uploader_bp',
    __name__,
    template_folder='templates',
    url_prefix='/learning_material_uploader'
)




def get_file_extension(filename):
    """Safely gets the file extension from a filename."""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return None




@learning_material_uploader_bp.route('/upload_page', methods=['GET'])
@login_required
def upload_material_page():
    file_form = FileUploadForm()
    link_form = LinkSubmitForm()
    
    return render_template(
        'learning_material_uploader/upload_material_page.html',
        page_title='Upload Learning Material',
        file_upload_form=file_form,
        link_submission_form=link_form
    )

# --- Feature 2: Handle the File Upload Submission ---
@learning_material_uploader_bp.route('/upload-file', methods=['POST'])
@login_required
def handle_file_upload():
    file_form = FileUploadForm()
    link_form = LinkSubmitForm()

    if file_form.validate_on_submit():
        file = file_form.learning_material_file.data
        original_filename = secure_filename(file.filename)
        extension = get_file_extension(original_filename)

        unique_id = uuid.uuid4().hex
        storage_filename = f"{unique_id}.{extension}"
        
        # Determine storage path from app config
        base_upload_folder = current_app.config.get('USER_UPLOADS_FOLDER', 'instance/user_uploads')
        user_specific_folder = os.path.join(base_upload_folder, str(current_user.id))
        
        try:
            os.makedirs(user_specific_folder, exist_ok=True)
            
            file_save_path_on_disk = os.path.join(user_specific_folder, storage_filename)
            
            file.save(file_save_path_on_disk)
            file_size = os.path.getsize(file_save_path_on_disk)

            new_material = LearningMaterial(
                user_id=current_user.id,
                title=original_filename,
                source_type='FILE',
                original_filename=original_filename,
                storage_filename=storage_filename,
                file_path=os.path.join(str(current_user.id), storage_filename), # Store a relative path
                mimetype=file.mimetype,
                extension=extension,
                size_bytes=file_size,
                processing_status='UPLOADED'
            )
            
            # Add to database session and commit
            db.session.add(new_material)
            db.session.commit()

            flash(f'File "{original_filename}" uploaded successfully! Processing will begin shortly.', 'success')
            
            # TODO: Trigger background task for text extraction here
            #AI USE : Gemini 2.5 Flash
            # e.g., text_extraction_task.delay(new_material.id)\
            
            create_roadmap_prompt = f"""
                    **Role:**
                    You are an expert technical writer and document indexer. Your task is to analyze a learning document and create a structured, hierarchical table of contents in JSON format.

                    **Context:**
                    The user has provided a complete learning document (file ). Your entire analysis must be based on the content and structure of this document, particularly its table of contents and chapter headings.
                    
                    
                    **Task:**
                    Analyze the entire document and create a hierarchical roadmap of its structure. For each major chapter and its primary subsections (e.g., 1.1, 1.2), you must extract the following information:
                    1.  **level**: The heading level (1 for a main chapter, 2 for a subsection).
                    2.  **title**: The full title of the chapter or section.
                    3.  **page_start**: The page number where it begins.
                    4.  **summary**: A concise, one-sentence summary describing the content of that specific section.

                    The final output should be a nested structure representing this hierarchy.

                    **Format and Constraints:**
                    - The entire output **MUST** be a single, valid JSON object.
                    - **DO NOT** add any text, explanations, or introductory remarks outside the JSON structure.
                    - The JSON object must have a `document_title` and a `structure` key. The `structure` key must contain a list of chapter objects, and each chapter object can contain a `subsections` list.

                    **Example of your required output:**
                    ```json
                    {{
                    "document_title": "A Brief History of Space Exploration",
                    "structure": [
                        {{
                        "level": 1,
                        "title": "1. The Early Days and the Space Race",
                        "page_start": 1,
                        "summary": "Covers the initial theories and the Cold War competition that fueled early space missions.",
                        "subsections": [
                            {{
                            "level": 2,
                            "title": "1.1 The V-2 Rocket and Post-War Development",
                            "page_start": 3,
                            "summary": "Details the role of German rocketry and its influence on early American and Soviet programs."
                            }},
                            {{
                            "level": 2,
                            "title": "1.2 Sputnik and the First Satellites",
                            "page_start": 15,
                            "summary": "Discusses the launch of Sputnik 1 and the beginning of the satellite era."
                            }}
                        ]
                        }},
                        {{
                        "level": 1,
                        "title": "2. The Apollo Program and the Moon Landing",
                        "page_start": 35,
                        "summary": "Focuses on the massive effort of the Apollo program, culminating in the first human landing on the Moon.",
                        "subsections": [
                            {{
                            "level": 2,
                            "title": "2.1 The Apollo 11 Mission",
                            "page_start": 58,
                            "summary": "Chronicles the historic mission of Neil Armstrong, Buzz Aldrin, and Michael Collins to the Moon."
                            }}
                        ]
                        }}
                    ]
                    if after this part is empty you need to analyze the file and if after this it is a text you need to extracted text:
                    }}"""

            #upload file to google server
            full_path_to_file = os.path.join(base_upload_folder, new_material.file_path)
            uploaded_file_object = genai.upload_file(
            path=full_path_to_file,
            display_name=new_material.title
            )
            if uploaded_file_object:
                 # The 'name' attribute contains the unique ID (e.g., 'files/abc123def456')
                new_material.gemini_file_uri = uploaded_file_object.name
                material_roadmap = request_ai(create_roadmap_prompt,uploaded_file_object)
                if material_roadmap :
                    new_material.analysis_roadmap = json.dumps(material_roadmap, indent= 2)
                    new_material.processing_status = 'COMPLETED'
                    flash(f'File "{original_filename}" processed successfully!', 'success')
                else:
                    new_material.processing_status = 'ANALYSIS_FAILED'
                    flash('The AI failed to analyze the document.', 'danger')
                db.session.commit()

            # Redirect user to a clean page to prevent form re-submission on refresh
            return redirect(url_for('.upload_material_page'))

        except Exception as e:
            current_app.logger.error(f"Error processing file upload for user {current_user.id}: {e}")
            db.session.rollback()  # Rollback DB changes if any part of the 'try' block failed
            flash('An unexpected error occurred while processing your file. Please try again.', 'danger')
            return redirect(url_for('.upload_material_page'))

    # If the form validation fails, re-render the upload page.
    # The 'file_form' object now contains the error messages, and your template
    # will automatically display them next to the correct field.
    return render_template(
        'learning_material_uploader/upload_material_page.html',
        page_title='Upload Learning Material',
        file_upload_form=file_form, 
        link_submission_form=link_form 
    )

@learning_material_uploader_bp.route('/submit-link', methods=['POST'])
@login_required
def handle_link_submission():
    link_form = LinkSubmitForm()
    file_form = FileUploadForm() 

    if link_form.validate_on_submit():
        url_submitted = link_form.material_url.data
        
        try:
            # Create a database record for the URL
            new_material = LearningMaterial(
                user_id=current_user.id,
                title=url_submitted, # Use URL as initial title
                source_type='URL',
                original_url=url_submitted,
                processing_status='PENDING_FETCH' # Set status for background worker
            )
            db.session.add(new_material)
            db.session.commit()

            flash(f'Link submitted successfully! We will process its content shortly.', 'success')

            # TODO: Trigger background task to fetch, parse, and extract text from the URL
            # e.g., url_content_extraction_task.delay(new_material.id)
            was_succesful,extracted_text = get_content(new_material.original_url)

            create_roadmap_prompt = f"""
                    **Role:**
                    You are an expert academic analyst and document indexer. Your task is to analyze a learning document and create a detailed, structured, and self-contained roadmap in JSON format.

                    **Context:**
                    The user has provided the following learning material as a single block of text. Your entire analysis must be based on this text.
                    ---
                    {extracted_text}
                    ---

                    **Task:**
                    Analyze the provided text and create a hierarchical roadmap of its structure. For each major chapter and primary subsection you identify, you MUST extract the following information:
                    1.  **level**: The heading level (1 for a main chapter, 2 for a subsection).
                    2.  **title**: The full title of the chapter or section.
                    3.  **summary**: A concise, one-sentence summary describing the content of that specific section.
                    4.  **content**: The **full and complete text** of that entire section, from its heading to the beginning of the next section.

                    The final output should be a nested JSON structure representing this hierarchy.

                    **Format and Constraints:**
                    - The entire output **MUST** be a single, valid JSON object.
                    - **DO NOT** add any text, explanations, or introductory remarks outside the JSON structure.
                    - The JSON object must have a `document_title` and a `structure` key. The `structure` key must contain a list of chapter objects, and each chapter object can contain a `subsections` list.
                    - Each object within the `structure` and `subsections` lists must contain the four keys: `level`, `title`, `summary`, and `content`.

                    **Example of your required output:**
                    ```json
                    {{
                    "document_title": "A Brief History of Space Exploration",
                    "structure": [
                        {{
                        "level": 1,
                        "title": "1. The Early Days and the Space Race",
                        "summary": "Covers the initial theories and the Cold War competition that fueled early space missions.",
                        "content": "The dream of space travel is as old as humanity itself, but it was not until the 20th century that it became a scientific possibility. The theoretical groundwork was laid by pioneers like Konstantin Tsiolkovsky... (and so on, with the full text of the entire chapter here)."
                        }},
                        {{
                        "level": 1,
                        "title": "2. The Apollo Program",
                        "summary": "Focuses on the massive effort of the Apollo program, culminating in the first human landing on the Moon.",
                        "content": "In response to the Soviet Union's early lead in the space race, President John F. Kennedy announced the ambitious goal of landing a man on the Moon... (and so on, with the full text of this chapter here)."
                        }}
                    ]
                    }}"""


            material_roadmap = request_ai(create_roadmap_prompt )
            if material_roadmap :
                new_material.analysis_roadmap = json.dumps(material_roadmap, indent= 2)
                new_material.processing_status = 'COMPLETED'
                flash(f'File "{new_material.original_filename}" processed successfully!', 'success')
            else:
                new_material.processing_status = 'ANALYSIS_FAILED'
                flash('The AI failed to analyze the document.', 'danger')
            db.session.commit()


            
            return redirect(url_for('.upload_material_page'))

        except Exception as e:
            current_app.logger.error(f"Error processing link submission for user {current_user.id}: {e}")
            db.session.rollback()
            flash('An unexpected error occurred while submitting your link. Please try again.', 'danger')
            return redirect(url_for('.upload_material_page'))

    return render_template(
        'learning_material_uploader/upload_material_page.html',
        page_title='Upload Learning Material',
        file_upload_form=file_form, 
        link_submission_form=link_form 
    )   

from flask import Blueprint, render_template, request, jsonify
from flaskstarter.learning_marterial_uploader.forms import FileUploadForm
import os
from werkzeug.utils import secure_filename

bp = Blueprint("learning_marterial_uploader", __name__)

@bp.route("/upload/ajax", methods=["POST"])
def handle_file_upload_ajax():
    form = FileUploadForm()
    if form.validate_on_submit():
        file = form.learning_material_file.data
        filename = secure_filename(file.filename)
        upload_folder = os.path.join("uploads")  # hoặc dùng current_app.config
        os.makedirs(upload_folder, exist_ok=True)
        file.save(os.path.join(upload_folder, filename))
        return jsonify(success=True, filename=filename)
    else:
        return jsonify(success=False, message="Upload failed. Maybe CSRF or missing file.")
