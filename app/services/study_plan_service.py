"""
Study Plan service for business logic related to AI-generated study plans
"""

from app import db
from app.models import StudyPlan, User
from app.exceptions import (
    ValidationError, AuthorizationError, NotFoundError
)
from app.utils.ai_generator import generate_study_plan


class StudyPlanService:
    """Service class for study plan operations"""
    
    @staticmethod
    def create_plan(user_id, subject, time_value, time_unit, knowledge_level):
        """
        Create a new AI-generated study plan.
        
        Args:
            user_id: ID of the user creating the plan
            subject: Subject to study
            time_value: Numeric value for study duration
            time_unit: Unit of time (days, weeks, months)
            knowledge_level: User's current knowledge level (beginner, intermediate, advanced)
            
        Returns:
            Created StudyPlan object
            
        Raises:
            ValidationError: If validation fails
            NotFoundError: If user not found
        """
        # Validate user exists
        user = User.query.get(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        # Validate subject
        if not subject or len(subject.strip()) < 2:
            raise ValidationError("Subject must be at least 2 characters long")
        
        if len(subject.strip()) > 100:
            raise ValidationError("Subject must not exceed 100 characters")
        
        # Validate time_value
        if not isinstance(time_value, int) or time_value <= 0:
            raise ValidationError("Time value must be a positive integer")
        
        if time_value > 365:
            raise ValidationError("Time value cannot exceed 365")
        
        # Validate time_unit
        valid_units = ['days', 'weeks', 'months']
        if time_unit not in valid_units:
            raise ValidationError(f"Time unit must be one of: {', '.join(valid_units)}")
        
        # Validate knowledge_level
        valid_levels = ['beginner', 'intermediate', 'advanced']
        if knowledge_level not in valid_levels:
            raise ValidationError(f"Knowledge level must be one of: {', '.join(valid_levels)}")
        
        # Generate the study plan using AI
        try:
            plan_content = generate_study_plan(
                subject=subject.strip(),
                time_value=time_value,
                time_unit=time_unit,
                knowledge_level=knowledge_level
            )
        except Exception as e:
            raise ValidationError(f"Error generating study plan: {str(e)}")
        
        # Validate plan content was generated
        if not plan_content or len(plan_content.strip()) < 20:
            raise ValidationError("Failed to generate valid study plan content")
        
        # Create StudyPlan record
        study_plan = StudyPlan(
            user_id=user_id,
            subject=subject.strip(),
            time_value=time_value,
            time_unit=time_unit,
            knowledge_level=knowledge_level,
            plan_content=plan_content
        )
        
        db.session.add(study_plan)
        db.session.commit()
        
        return study_plan
    
    @staticmethod
    def delete_plan(plan_id, user_id):
        """
        Delete a study plan.
        
        Args:
            plan_id: ID of the plan to delete
            user_id: ID of the user making the deletion
            
        Raises:
            NotFoundError: If plan not found
            AuthorizationError: If user doesn't own the plan
        """
        plan = StudyPlan.query.get(plan_id)
        if not plan:
            raise NotFoundError(f"Study plan with id {plan_id} not found")
        
        if plan.user_id != user_id:
            raise AuthorizationError("You don't have permission to delete this plan")
        
        db.session.delete(plan)
        db.session.commit()
    
    @staticmethod
    def get_plan(plan_id, user_id):
        """
        Get a study plan with authorization check.
        
        Args:
            plan_id: ID of the plan to retrieve
            user_id: ID of the user requesting the plan
            
        Returns:
            StudyPlan object
            
        Raises:
            NotFoundError: If plan not found
            AuthorizationError: If user doesn't own the plan
        """
        plan = StudyPlan.query.get(plan_id)
        if not plan:
            raise NotFoundError(f"Study plan with id {plan_id} not found")
        
        if plan.user_id != user_id:
            raise AuthorizationError("You don't have permission to view this plan")
        
        return plan
    
    @staticmethod
    def get_user_plans(user_id, limit=None):
        """
        Get all study plans for a user.
        
        Args:
            user_id: ID of the user
            limit: Optional limit on number of plans to return
            
        Returns:
            List of StudyPlan objects ordered by created_at DESC
            
        Raises:
            NotFoundError: If user not found
        """
        user = User.query.get(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        query = StudyPlan.query.filter_by(user_id=user_id)\
            .order_by(StudyPlan.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
