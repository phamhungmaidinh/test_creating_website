# In flaskstarter/learning_materials/forms.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SubmitField, URLField
from wtforms.validators import DataRequired, URL, Length

ALLOWED_EXTENSIONS = ['pdf', 'docx', 'txt', 'pptx', 'md']

class FileUploadForm(FlaskForm):
    learning_material_file = FileField(
        'Select or Drag & Drop Your File', 
        validators=[
            FileRequired(message='Please select a file to upload.'),
            FileAllowed(
                ALLOWED_EXTENSIONS, 
                message=f'Invalid file type. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}'
            )
        ]
    )
    
    submit = SubmitField('Upload File')



class LinkSubmitForm(FlaskForm):
    material_url = URLField(
        'Learning Material URL:',
        validators=[
            DataRequired(message='Please enter a URL.'),
            URL(message='The URL you entered is not valid.')
        ],
        render_kw={"placeholder": "https://example.com/your-resource"}
    )

    submit = SubmitField('Submit Link')