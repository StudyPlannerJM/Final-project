"""
Study Plan service for business logic related to AI-generated study plans
"""

from datetime import datetime, timedelta, timezone
import re

from app import db
from app.models import StudyPlan, User, Category
from app.exceptions import (
    ValidationError, AuthorizationError, NotFoundError
)
from app.utils.ai_generator import generate_study_plan
from app.services.task_service import TaskService


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
        user = db.session.get(User, user_id)
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
        plan = db.session.get(StudyPlan, plan_id)
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
        plan = db.session.get(StudyPlan, plan_id)
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
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        query = StudyPlan.query.filter_by(user_id=user_id)\
            .order_by(StudyPlan.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()

    @staticmethod
    def create_tasks_from_plan(plan, user_id, num_tasks=1):
        """
        Create simple tasks from an existing study plan.

        Args:
            plan: StudyPlan object
            user_id: ID of the user creating tasks
            num_tasks: Number of tasks to create

        Returns:
            List of created Task objects

        Raises:
            ValidationError: If inputs are invalid
            AuthorizationError: If user doesn't own the plan
        """
        if not plan:
            raise ValidationError("Study plan is required")

        if plan.user_id != user_id:
            raise AuthorizationError("You don't have permission to use this plan")

        if not isinstance(num_tasks, int):
            raise ValidationError("Number of tasks must be an integer")

        if num_tasks < 1 or num_tasks > 5:
            raise ValidationError("Number of tasks must be between 1 and 5")

        candidates = StudyPlanService._extract_task_candidates(plan.plan_content)
        selected = candidates[:num_tasks]

        if not selected:
            return []

        category = StudyPlanService._get_or_create_plan_category(user_id, plan.subject)
        due_dates = StudyPlanService._build_distributed_due_dates(plan, len(selected))

        created_tasks = []
        for idx, task_title in enumerate(selected):
            due_date = due_dates[idx] if idx < len(due_dates) else None

            task = TaskService.create_task(
                user_id=user_id,
                title=task_title,
                description=f"Auto-created from study plan: {plan.subject}",
                due_date=due_date,
                category_id=category.id
            )
            created_tasks.append(task)

        return created_tasks

    @staticmethod
    def _extract_task_candidates(plan_content):
        """Extract actionable task titles from markdown-like plan content."""
        if not plan_content:
            return []

        bullet_pattern = re.compile(r'^\s*(?:[-*•]|\d+[.)])\s+(.+)$')
        checkbox_pattern = re.compile(r'^\s*[-*]\s*\[[ xX]\]\s+(.+)$')
        timeline_pattern = re.compile(
            r'^\s*(?:week|day|phase|milestone)\s*\d+\s*[:\-]\s*(.+)$',
            re.IGNORECASE
        )

        tasks = []
        seen = set()

        for raw_line in plan_content.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith('#'):
                continue

            match = checkbox_pattern.match(line)
            if not match:
                match = bullet_pattern.match(line)
            if not match:
                match = timeline_pattern.match(line)

            if not match:
                continue

            normalized = StudyPlanService._normalize_task_text(match.group(1))
            if not normalized:
                continue

            lookup_key = normalized.lower()
            if lookup_key in seen:
                continue

            seen.add(lookup_key)
            tasks.append(normalized)

        return tasks

    @staticmethod
    def _normalize_task_text(text):
        """Clean markdown artifacts and return a valid short task title."""
        if not text:
            return None

        cleaned = text.strip()
        cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
        cleaned = re.sub(r'[`*_~>#]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip(' .;:-')

        if len(cleaned) < 3:
            return None

        if len(cleaned) > 100:
            cleaned = cleaned[:100].rstrip()

        return cleaned

    @staticmethod
    def _get_or_create_plan_category(user_id, subject):
        """Get or create a category dedicated to generated study-plan tasks."""
        category_name = f"Study Plan: {subject.strip()}"[:100]
        category = Category.query.filter_by(user_id=user_id, name=category_name).first()
        if category:
            if category.icon == 'fa-graduation-cap':
                category.icon = None
                db.session.flush()
            return category

        category = Category(
            name=category_name,
            user_id=user_id,
            is_default=False
        )
        db.session.add(category)
        db.session.flush()
        return category

    @staticmethod
    def _build_distributed_due_dates(plan, total_tasks):
        """Distribute due dates from plan start to plan end."""
        if total_tasks <= 0:
            return []

        start_date = plan.created_at or datetime.now(timezone.utc)
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)

        unit_days = {
            'days': 1,
            'weeks': 7,
            'months': 30,
        }

        duration_days = plan.time_value * unit_days.get(plan.time_unit, 0)
        if duration_days <= 0:
            return [None] * total_tasks

        end_date = start_date + timedelta(days=duration_days)
        if total_tasks == 1:
            return [end_date]

        step = (end_date - start_date) / total_tasks
        return [start_date + (step * (idx + 1)) for idx in range(total_tasks)]
