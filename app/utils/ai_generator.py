# ==============================================================================
# AI STUDY PLAN GENERATOR
# Uses Google Gemini AI to generate personalized study plans
# ==============================================================================

try:
    from google import genai
except ImportError:
    genai = None  # Will handle this in the functions
from flask import current_app


def configure_gemini_api():
    """Configure the Google Gemini API with the API key"""
    if genai is None:
        raise ImportError("Google Generative AI library is not installed. Run: pip install google-generativeai")
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured")
    client = genai.Client(api_key=api_key)
    return client


def generate_study_plan(subject, time_value, time_unit, knowledge_level):
    """
    Generate a personalized study plan using Google Gemini AI
    
    Args:
        subject (str): The subject or topic to study
        time_value (int): Number of time units
        time_unit (str): Unit of time ('days', 'weeks', or 'months')
        knowledge_level (str): Current knowledge level (beginner, intermediate, advanced)
    
    Returns:
        str: Generated study plan in formatted text
    """
    try:
        # Configure the API
        client = configure_gemini_api()
        
        # Convert time to days for calculations
        if time_unit == 'days':
            total_days = time_value
            time_display = f"{time_value} {'day' if time_value == 1 else 'days'}"
        elif time_unit == 'weeks':
            total_days = time_value * 7
            time_display = f"{time_value} {'week' if time_value == 1 else 'weeks'}"
        elif time_unit == 'months':
            total_days = time_value * 30  # Approximate
            time_display = f"{time_value} {'month' if time_value == 1 else 'months'}"
        else:
            total_days = time_value
            time_display = f"{time_value} days"
        
        # Create the prompt for the AI
        prompt = f"""
You are an expert educational advisor. Create a personalized study plan.

**Subject:** {subject}
**Available Time:** {time_display} ({total_days} days)
**Knowledge Level:** {knowledge_level}

IMPORTANT: Follow this EXACT structure and formatting:

# 📋 Overview
- Clear learning goal 1
- Clear learning goal 2
- Expected outcome after completion

# 📅 Study Schedule
Break down the {time_display} into clear phases:

## Phase 1: Foundation ({knowledge_level} level)
- Topics to cover
- Key concepts to master
- Time allocation

## Phase 2: Practice & Application
- Hands-on exercises
- Practice problems
- Projects or assignments

## Phase 3: Review & Mastery
- Review key concepts
- Take practice tests
- Final preparations

# 📖 Study Methods
Effective techniques for {knowledge_level} learners:
- Active recall and spaced repetition
- Practice with real problems
- Teach concepts to others
- Use {subject}-specific resources

# ✅ Milestones & Assessment
- Week 1: Complete foundation topics
- Week 2: Finish practice exercises
- Regular: Self-test every 3 days
- Final: Complete mock assessment

# 💡 Success Tips
- Tip 1: Stay consistent with daily study schedule
- Tip 2: Focus on understanding, not memorization
- Tip 3: Use active learning techniques
- Tip 4: Take breaks using Pomodoro technique
- Tip 5: Track your progress regularly

FORMATTING RULES:
- Use # for main sections (ONLY 5 sections as shown)
- Use ## for subsections within Study Schedule
- Use - for all bullet points
- Use **bold** for emphasis on key terms
- Keep content concise and actionable
- Maintain consistent spacing
"""
        
        # Generate the study plan using the new API
        # Using gemini-flash-latest for better availability
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        
        # Return the generated text
        return response.text
        
    except Exception as e:
        current_app.logger.error(f"Error generating study plan: {str(e)}")
        return f"Error generating study plan: {str(e)}"


def format_plan_for_display(plan_content):
    """
    Format the AI-generated plan for better HTML display
    with proper markdown conversion
    
    Args:
        plan_content (str): Raw plan content from AI with markdown
    
    Returns:
        str: Formatted HTML content
    """
    import re
    
    # Split into lines for processing
    lines = plan_content.split('\n')
    formatted_lines = []
    in_list = False
    in_numbered_list = False
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines and add spacing
        if not stripped:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            if in_numbered_list:
                formatted_lines.append('</ol>')
                in_numbered_list = False
            formatted_lines.append('<div class="section-spacing"></div>')
            continue
        
        # Main headers (# Header)
        if stripped.startswith('# ') and not stripped.startswith('## '):
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            if in_numbered_list:
                formatted_lines.append('</ol>')
                in_numbered_list = False
            header_text = stripped[2:].strip()
            formatted_lines.append(
                f'<h2 class="plan-section-header">{header_text}</h2>'
            )
        
        # Subheaders (## Subheader)
        elif stripped.startswith('## '):
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            if in_numbered_list:
                formatted_lines.append('</ol>')
                in_numbered_list = False
            header_text = stripped[3:].strip()
            formatted_lines.append(
                f'<h3 class="plan-subsection-header">{header_text}</h3>'
            )
        
        # Numbered list items (1. , 2. , etc.)
        elif re.match(r'^\d+\.\s+', stripped):
            item_text = re.sub(r'^\d+\.\s+', '', stripped)
            # Format **bold** and *italic*
            item_text = re.sub(
                r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', item_text
            )
            item_text = re.sub(
                r'(?<!\*)\*(?!\*)([^*]+)\*(?!\*)', r'<em>\1</em>', item_text
            )
            
            if not in_numbered_list:
                if in_list:
                    formatted_lines.append('</ul>')
                    in_list = False
                formatted_lines.append('<ol class="plan-numbered-list">')
                in_numbered_list = True
            formatted_lines.append(f'<li>{item_text}</li>')
        
        # Bullet points (- item or * item)
        elif stripped.startswith('- ') or stripped.startswith('* '):
            if in_numbered_list:
                formatted_lines.append('</ol>')
                in_numbered_list = False
            
            item_text = stripped[2:].strip()
            # Format **bold** and *italic*
            item_text = re.sub(
                r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', item_text
            )
            item_text = re.sub(
                r'(?<!\*)\*(?!\*)([^*]+)\*(?!\*)', r'<em>\1</em>', item_text
            )
            
            if not in_list:
                formatted_lines.append('<ul class="plan-list">')
                in_list = True
            formatted_lines.append(f'<li>{item_text}</li>')
        
        # Regular paragraph text
        else:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            if in_numbered_list:
                formatted_lines.append('</ol>')
                in_numbered_list = False
            
            # Format **bold** and *italic*
            text = re.sub(
                r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', stripped
            )
            text = re.sub(
                r'(?<!\*)\*(?!\*)([^*]+)\*(?!\*)', r'<em>\1</em>', text
            )
            formatted_lines.append(f'<p class="plan-paragraph">{text}</p>')
    
    # Close any open lists
    if in_list:
        formatted_lines.append('</ul>')
    if in_numbered_list:
        formatted_lines.append('</ol>')
    
    return '\n'.join(formatted_lines)
