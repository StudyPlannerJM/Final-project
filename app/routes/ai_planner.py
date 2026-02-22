"""
AI Planner Blueprint - AI-powered study plan generation routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.forms import StudyPlanForm
from app.models import StudyPlan
from app import db
from app.utils.ai_generator import generate_study_plan, format_plan_for_display

ai_planner_bp = Blueprint('ai_planner', __name__, url_prefix='/ai-planner')


@ai_planner_bp.route('/generator', methods=['GET', 'POST'])
@login_required
def generator():
    """AI-powered study plan generator page"""
    form = StudyPlanForm()
    
    if form.validate_on_submit():
        try:
            # Generate the study plan using AI
            plan_content = generate_study_plan(
                subject=form.subject.data,
                time_value=form.time_value.data,
                time_unit=form.time_unit.data,
                knowledge_level=form.knowledge_level.data
            )
            
            # Save the plan to database
            study_plan = StudyPlan(
                user_id=current_user.id,
                subject=form.subject.data,
                time_value=form.time_value.data,
                time_unit=form.time_unit.data,
                knowledge_level=form.knowledge_level.data,
                plan_content=plan_content
            )
            
            db.session.add(study_plan)
            db.session.commit()
            
            flash('Study plan generated successfully!', 'success')
            return redirect(url_for('ai_planner.view_plan', plan_id=study_plan.id))
            
        except Exception as e:
            flash(f'Error generating study plan: {str(e)}', 'danger')
            current_app.logger.error(f"AI Plan Generation Error: {str(e)}")
    
    # Get user's previous plans
    previous_plans = StudyPlan.query.filter_by(user_id=current_user.id)\
        .order_by(StudyPlan.created_at.desc()).limit(5).all()
    
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
    plan = StudyPlan.query.get_or_404(plan_id)
    
    # Security check - verify user owns this plan
    if plan.user_id != current_user.id:
        flash('You are not authorized to view this plan.', 'danger')
        return redirect(url_for('ai_planner.generator'))
    
    # Format the plan content for display
    formatted_content = format_plan_for_display(plan.plan_content)
    
    return render_template(
        'ai_planner/view_study_plan.html',
        title=f'Study Plan: {plan.subject}',
        plan=plan,
        formatted_content=formatted_content
    )


@ai_planner_bp.route('/my-plans')
@login_required
def my_plans():
    """View all user's study plans"""
    plans = StudyPlan.query.filter_by(user_id=current_user.id)\
        .order_by(StudyPlan.created_at.desc()).all()
    
    return render_template(
        'ai_planner/my_study_plans.html',
        title='My Study Plans',
        plans=plans
    )


@ai_planner_bp.route('/delete/<int:plan_id>', methods=['POST'])
@login_required
def delete_plan(plan_id):
    """Delete a study plan"""
    plan = StudyPlan.query.get_or_404(plan_id)
    
    # Security check - verify user owns this plan
    if plan.user_id != current_user.id:
        flash('You are not authorized to delete this plan.', 'danger')
        return redirect(url_for('ai_planner.generator'))
    
    db.session.delete(plan)
    db.session.commit()
    flash('Study plan deleted successfully!', 'success')
    return redirect(url_for('ai_planner.generator'))
