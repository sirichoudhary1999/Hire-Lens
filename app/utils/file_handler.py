import os
from werkzeug.utils import secure_filename
from flask import current_app
import PyPDF2
from docx import Document

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def validate_file_upload(file):
    """Validate file upload (extension, size)."""
    if not file or file.filename == '':
        return False, "No file provided"

    if not allowed_file(file.filename):
        return False, "File type not allowed. Only PDF and DOCX files are supported"

    return True, "File is valid"

def save_uploaded_file(file, user_id, resume_id):
    """
    Save uploaded file to user-specific directory.
    Returns: (file_path, original_filename, file_type, file_size) or (None, None, None, None) on error
    """
    if not file:
        return None, None, None, None

    filename = secure_filename(file.filename)
    file_type = filename.rsplit('.', 1)[1].lower()

    # Create user-specific directory
    user_dir = os.path.join(current_app.config['RESUME_FOLDER'], f'user_{user_id}')
    os.makedirs(user_dir, exist_ok=True)

    # Generate unique filename with resume_id
    import time
    timestamp = int(time.time())
    new_filename = f"{resume_id}_{timestamp}.{file_type}"
    file_path = os.path.join(user_dir, new_filename)

    # Save file
    file.save(file_path)

    # Get file size
    file_size = os.path.getsize(file_path)

    return file_path, filename, file_type, file_size

def extract_text_from_pdf(file_path):
    """Extract text from PDF file."""
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def extract_text_from_docx(file_path):
    """Extract text from DOCX file."""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract text from DOCX: {str(e)}")

def extract_text_from_file(file_path, file_type):
    """Extract text based on file type."""
    if file_type == 'pdf':
        return extract_text_from_pdf(file_path)
    elif file_type == 'docx':
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

def delete_resume_file(file_path):
    """Delete resume file from filesystem."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        raise Exception(f"Failed to delete file: {str(e)}")
