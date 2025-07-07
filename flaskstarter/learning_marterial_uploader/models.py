
from ..extensions import db 
from datetime import datetime

class LearningMaterial(db.Model):
    __tablename__ = 'learning_materials' 

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    # User-provided or extracted title for the material
    title = db.Column(db.String(255), nullable=True) 

    # Type of the source: 'FILE' or 'URL'
    source_type = db.Column(db.String(10), nullable=False)  

    # Timestamps
    upload_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_accessed_timestamp = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow) # Updates when record is modified, or can be set manually

    # --- Fields primarily for source_type = 'FILE' ---
    original_filename = db.Column(db.String(255), nullable=True)  # The user's original name for the file
    storage_filename = db.Column(db.String(255), unique=True, nullable=True) # Unique filename used for storage on your server/cloud (e.g., UUID.extension)
    file_path = db.Column(db.String(512), nullable=True)          # The actual storage path (relative to an upload root or full cloud URI)
    mimetype = db.Column(db.String(100), nullable=True)           # e.g., 'application/pdf', 'image/png'
    extension = db.Column(db.String(10), nullable=True)           # e.g., 'pdf', 'docx'
    size_bytes = db.Column(db.BigInteger, nullable=True)          # File size in bytes, use BigInteger for large files

    original_url = db.Column(db.String(2048), nullable=True)      # The URL submitted by the user

    # --- Processing & Content Fields ---
    processing_status = db.Column(db.String(50), nullable=False, default='NEW')  # e.g., 'NEW', 'UPLOADED', 'TEXT_EXTRACTION_PENDING', 'TEXT_EXTRACTED', 'AI_ANALYSIS_PENDING', 'AI_ANALYZED', 'ERROR_EXTRACTION', 'ERROR_AI'
    
    # Path to where the extracted plain text content from the file/URL is stored.
    # This is what you'll typically feed to AI models that consume text.
    analysis_roadmap = db.Column(db.Text, nullable=True) 
    
    # Optional: A hash of the original file content to detect/prevent duplicate uploads if desired.
    content_hash = db.Column(db.String(64), nullable=True, index=True)

    # link for the uploaded file
    gemini_file_uri = db.Column(db.String(100), nullable=True) # Store identified topics (e.g., as a JSON string or comma-separated list)
    


    def __repr__(self):
        """Provides a developer-friendly string representation of the object."""
        name = self.title or self.original_filename or self.original_url or f"ID: {self.id}"
        return f'<LearningMaterial "{name}">'

    