"""
Summarizer Blueprint - Document upload and summary generation routes
"""
import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import Summary
from app import db
from app.summarizer import (
    get_allowed_extensions,
    get_file_type,
    extract_text,
    generate_summary
)

summarizer_bp = Blueprint('summarizer', __name__, url_prefix='/summarizer')


def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in get_allowed_extensions()


@summarizer_bp.route('/')
@login_required
def index():
    """Display all summaries for the current user"""
    user_summaries = Summary.query.filter_by(
        author=current_user
    ).order_by(Summary.date_created.desc()).all()
    return render_template(
        'summarizer/summarizer.html', title='Summarizer', summaries=user_summaries
    )


@summarizer_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload a file and create a summary"""
    if request.method == 'POST':
        # STEP 1: Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected. Please choose a file to upload.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # STEP 2: Check if a file was actually selected
        if file.filename == '':
            flash('No file selected. Please choose a file to upload.', 'danger')
            return redirect(request.url)
        
        # STEP 3: Validate file type
        if not allowed_file(file.filename):
            flash('Invalid file type. Allowed types: PDF, DOCX, JPG, PNG, GIF, BMP, TIFF', 'danger')
            return redirect(request.url)
        
        # STEP 4: Get the title from form or use filename
        title = request.form.get('title', '').strip()
        if not title:
            title = os.path.splitext(file.filename)[0]
        
        # STEP 5: Save the file temporarily
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(current_app.root_path, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        try:
            # STEP 6: Determine file type and extract text
            file_type = get_file_type(filename)
            
            # Check if user wants to use OCR for PDF
            use_ocr = request.form.get('use_ocr') == 'on'
            if file_type == 'pdf' and use_ocr:
                file_type = 'ocr'
            
            success, result = extract_text(file_path, file_type)
            
            if not success:
                flash(f'Error extracting text: {result}', 'danger')
                return redirect(request.url)
            
            extracted_text = result
            
            # STEP 7: Generate summary
            summary_text = generate_summary(extracted_text)
            
            # STEP 8: Create new Summary record
            new_summary = Summary(
                title=title,
                original_filename=filename,
                extracted_text=extracted_text,
                summary_text=summary_text,
                file_type=file_type,
                author=current_user
            )
            
            db.session.add(new_summary)
            db.session.commit()
            
            flash('Document processed successfully! Summary created.', 'success')
            return redirect(url_for('summarizer.view', summary_id=new_summary.id))
            
        except Exception as e:
            flash(f'Error processing document: {str(e)}', 'danger')
            return redirect(request.url)
        finally:
            # STEP 9: Clean up - delete temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    return render_template('summarizer/upload_summary.html', title='Upload Document')


@summarizer_bp.route('/view/<int:summary_id>')
@login_required
def view(summary_id):
    """View a specific summary"""
    summary = Summary.query.get_or_404(summary_id)
    
    # Security check - verify user owns this summary
    if summary.author != current_user:
        flash('You are not authorized to view this summary.', 'danger')
        return redirect(url_for('summarizer.index'))
    
    return render_template(
        'summarizer/view_summary.html', title='View Summary', summary=summary
    )


@summarizer_bp.route('/delete/<int:summary_id>', methods=['POST'])
@login_required
def delete(summary_id):
    """Delete a summary"""
    summary = Summary.query.get_or_404(summary_id)
    
    # Security check - verify user owns this summary
    if summary.author != current_user:
        flash('You are not authorized to delete this summary.', 'danger')
        return redirect(url_for('summarizer.index'))
    
    db.session.delete(summary)
    db.session.commit()
    flash('Summary deleted successfully!', 'success')
    return redirect(url_for('summarizer.index'))
