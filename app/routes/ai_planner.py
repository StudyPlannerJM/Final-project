"""
AI Planner Blueprint - AI-powered study plan generation routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.forms import StudyPlanForm
from app.services import StudyPlanService
from app.utils.ai_generator import format_plan_for_display
from app.exceptions import ValidationError, AuthorizationError, NotFoundError

ai_planner_bp = Blueprint('ai_planner', __name__, url_prefix='/ai-planner')


@ai_planner_bp.route('/generator', methods=['GET', 'POST'])
@login_required
def generator():
    """AI-powered study plan generator page"""
    form = StudyPlanForm()
    
    if form.validate_on_submit():
        try:
            # Generate and save the plan using service
            study_plan = StudyPlanService.create_plan(
                user_id=current_user.id,
                subject=form.subject.data,
                time_value=form.time_value.data,
                time_unit=form.time_unit.data,
                knowledge_level=form.knowledge_level.data
            )
            
            flash('Study plan generated successfully!', 'success')
            return redirect(url_for('ai_planner.view_plan', plan_id=study_plan.id))
            
        except ValidationError as e:
            flash(str(e), 'danger')
        except NotFoundError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'Error generating study plan: {str(e)}', 'danger')
            current_app.logger.error(f"AI Plan Generation Error: {str(e)}")
    
    # Get user's previous plans using service
    try:
        previous_plans = StudyPlanService.get_user_plans(current_user.id, limit=5)
    except NotFoundError:
        previous_plans = []
    
    return render_template(
        'ai_planner/ai_plan_generator.html',
        title='AI Study Plan Generator',
        form=form,
        previous_plans=previous_plans
    )


@ai_planner_bp.route('/view/<int:plan_id>')
@login_required
def view_plan(plan_id):
    """View a specific study plan"""
    try:
        # Get plan with authorization check using service
        plan = StudyPlanService.get_plan(plan_id, current_user.id)
        
        # Format the plan content for display
        formatted_content = format_plan_for_display(plan.plan_content)
        
        return render_template(
            'ai_planner/view_study_plan.html',
            title=f'Study Plan: {plan.subject}',
            plan=plan,
            formatted_content=formatted_content
        )
    except (NotFoundError, AuthorizationError) as e:
        flash(str(e), 'danger')
        return redirect(url_for('ai_planner.generator'))


@ai_planner_bp.route('/my-plans')
@login_required
def my_plans():
    """View all user's study plans"""
    try:
        plans = StudyPlanService.get_user_plans(current_user.id)
        return render_template(
            'ai_planner/my_study_plans.html',
            title='My Study Plans',
            plans=plans
        )
    except NotFoundError as e:
        flash(str(e), 'danger')
        return redirect(url_for('ai_planner.generator'))


@ai_planner_bp.route('/delete/<int:plan_id>', methods=['POST'])
@login_required
def delete_plan(plan_id):
    """Delete a study plan"""
    try:
        StudyPlanService.delete_plan(plan_id, current_user.id)
        flash('Study plan deleted successfully!', 'success')
        return redirect(url_for('ai_planner.generator'))
    except (NotFoundError, AuthorizationError) as e:
        flash(str(e), 'danger')
        return redirect(url_for('ai_planner.generator'))
