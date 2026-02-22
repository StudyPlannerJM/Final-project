"""
Summarizer Blueprint - Document upload and summary generation routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.services import SummaryService
from app.exceptions import ValidationError, AuthorizationError, NotFoundError

summarizer_bp = Blueprint('summarizer', __name__, url_prefix='/summarizer')


@summarizer_bp.route('/')
@login_required
def index():
    """Display all summaries for the current user"""
    try:
        user_summaries = SummaryService.get_user_summaries(current_user.id)
        return render_template(
            'summarizer/summarizer.html', title='Summarizer', summaries=user_summaries
        )
    except NotFoundError as e:
        flash(str(e), 'danger')
        return redirect(url_for('main.index'))


@summarizer_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload a file and create a summary"""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected. Please choose a file to upload.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Check if a file was actually selected
        if file.filename == '':
            flash('No file selected. Please choose a file to upload.', 'danger')
            return redirect(request.url)
        
        # Get the title from form
        title = request.form.get('title', '').strip()
        
        # Check if user wants to use OCR for PDF
        use_ocr = request.form.get('use_ocr') == 'on'
        
        # Get upload folder path
        upload_folder = current_app.root_path + '/uploads'
        
        try:
            # Create summary using service
            new_summary = SummaryService.create_summary_from_file(
                user_id=current_user.id,
                file=file,
                title=title,
                use_ocr=use_ocr,
                upload_folder=upload_folder
            )
            
            flash('Document processed successfully! Summary created.', 'success')
            return redirect(url_for('summarizer.view', summary_id=new_summary.id))
            
        except ValidationError as e:
            flash(str(e), 'danger')
            return redirect(request.url)
        except NotFoundError as e:
            flash(str(e), 'danger')
            return redirect(request.url)
        except Exception as e:
            flash(f'Error processing document: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('summarizer/upload_summary.html', title='Upload Document')


@summarizer_bp.route('/view/<int:summary_id>')
@login_required
def view(summary_id):
    """View a specific summary"""
    try:
        summary = SummaryService.get_summary(summary_id, current_user.id)
        return render_template(
            'summarizer/view_summary.html', title='View Summary', summary=summary
        )
    except (NotFoundError, AuthorizationError) as e:
        flash(str(e), 'danger')
        return redirect(url_for('summarizer.index'))


@summarizer_bp.route('/delete/<int:summary_id>', methods=['POST'])
@login_required
def delete(summary_id):
    """Delete a summary"""
    try:
        SummaryService.delete_summary(summary_id, current_user.id)
        flash('Summary deleted successfully!', 'success')
        return redirect(url_for('summarizer.index'))
    except (NotFoundError, AuthorizationError) as e:
        flash(str(e), 'danger')
        return redirect(url_for('summarizer.index'))
