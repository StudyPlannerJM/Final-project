"""
Summary service for business logic related to document summaries
"""

import os
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from app import db
from app.models import Summary, User
from app.exceptions import (
    ValidationError, AuthorizationError, NotFoundError
)
from app.utils.document_processor import (
    get_allowed_extensions,
    get_file_type,
    extract_text,
    generate_summary
)


class SummaryService:
    """Service class for summary operations"""
    
    @staticmethod
    def allowed_file(filename):
        """Check if the file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in get_allowed_extensions()
    
    @staticmethod
    def create_summary_from_file(user_id, file, title=None, use_ocr=False, upload_folder=None):
        """
        Create a new summary from an uploaded file.
        
        Args:
            user_id: ID of the user creating the summary
            file: FileStorage object from request.files
            title: Optional custom title (will use filename if not provided)
            use_ocr: Whether to use OCR for PDF files
            upload_folder: Path to upload folder (must be provided)
            
        Returns:
            Created Summary object
            
        Raises:
            ValidationError: If validation fails
            NotFoundError: If user not found
        """
        # Validate user exists
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        # Validate file was provided
        if not file or not file.filename:
            raise ValidationError("No file selected. Please choose a file to upload.")
        
        # Validate file type
        if not SummaryService.allowed_file(file.filename):
            raise ValidationError(
                "Invalid file type. Allowed types: PDF, DOCX, JPG, PNG, GIF, BMP, TIFF"
            )
        
        # Get title from parameter or use filename
        if not title or not title.strip():
            title = os.path.splitext(file.filename)[0]
        title = title.strip()
        
        # Validate title length
        if len(title) > 200:
            raise ValidationError("Title must not exceed 200 characters")
        
        # Secure the filename and save temporarily
        filename = secure_filename(file.filename)
        if not upload_folder:
            raise ValidationError("Upload folder path must be provided")
        
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        
        try:
            # Save the file
            file.save(file_path)
            
            # Determine file type
            file_type = get_file_type(filename)
            
            # Use OCR for PDF if requested
            if file_type == 'pdf' and use_ocr:
                file_type = 'ocr'
            
            # Extract text from file
            success, result = extract_text(file_path, file_type)
            
            if not success:
                raise ValidationError(f"Error extracting text: {result}")
            
            extracted_text = result
            
            # Validate extracted text
            if not extracted_text or len(extracted_text.strip()) < 10:
                raise ValidationError(
                    "Could not extract sufficient text from the document"
                )
            
            # Generate summary using AI
            summary_text = generate_summary(extracted_text)
            
            # Create Summary record
            new_summary = Summary(
                title=title,
                original_filename=filename,
                extracted_text=extracted_text,
                summary_text=summary_text,
                file_type=file_type,
                user_id=user_id
            )
            
            db.session.add(new_summary)
            db.session.commit()
            
            return new_summary
            
        finally:
            # Clean up - delete temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    @staticmethod
    def delete_summary(summary_id, user_id):
        """
        Delete a summary.
        
        Args:
            summary_id: ID of the summary to delete
            user_id: ID of the user making the deletion
            
        Raises:
            NotFoundError: If summary not found
            AuthorizationError: If user doesn't own the summary
        """
        summary = db.session.get(Summary, summary_id)
        if not summary:
            raise NotFoundError(f"Summary with id {summary_id} not found")
        
        if summary.user_id != user_id:
            raise AuthorizationError("You don't have permission to delete this summary")
        
        db.session.delete(summary)
        db.session.commit()
    
    @staticmethod
    def get_summary(summary_id, user_id):
        """
        Get a summary with authorization check.
        
        Args:
            summary_id: ID of the summary to retrieve
            user_id: ID of the user requesting the summary
            
        Returns:
            Summary object
            
        Raises:
            NotFoundError: If summary not found
            AuthorizationError: If user doesn't own the summary
        """
        summary = db.session.get(Summary, summary_id)
        if not summary:
            raise NotFoundError(f"Summary with id {summary_id} not found")
        
        if summary.user_id != user_id:
            raise AuthorizationError("You don't have permission to view this summary")
        
        return summary
    
    @staticmethod
    def get_user_summaries(user_id):
        """
        Get all summaries for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of Summary objects ordered by date_created DESC
            
        Raises:
            NotFoundError: If user not found
        """
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        return Summary.query.filter_by(
            user_id=user_id
        ).order_by(Summary.date_created.desc()).all()
