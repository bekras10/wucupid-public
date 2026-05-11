from flask import Blueprint, jsonify, current_app, request
from flask_cors import cross_origin
from datetime import datetime, timedelta
import pytz
from ..models.cycle import get_current_cycle, check_cycle_status, initialize_cycle_table, get_central_time
import threading
import time
import openai
from .. import db
from ..models.models import User, SurveyResponse, Match as MatchModel, MatchingCycle, MatchingAttempt
from sqlalchemy import desc, text
import os
from dotenv import load_dotenv
from ..services.cycle_orchestrator import run_cycle_tick

# Load API key from environment
load_dotenv()
openai_api_key = os.environ.get("OPENAI_API_KEY")
if openai_api_key:
    openai.api_key = openai_api_key
    print(f"OpenAI API key loaded in cycle.py (length: {len(openai_api_key)})")
else:
    print("WARNING: OpenAI API key not found in environment variables for cycle.py!")

cycle_bp = Blueprint('cycle', __name__)
app_instance = None  # Global variable to store the app instance

def init_cycle_system(app):
    """Initialize cycle table"""
    global app_instance
    app_instance = app
    
    current_app.logger.info("init_cycle_system_enter")
    
    try:
        initialize_cycle_table()
        current_app.logger.info("cycle_table_initialized (no background thread)")
    except Exception:
        current_app.logger.exception("cycle_init_error")
    return True

@cycle_bp.route('/', methods=['GET'])
def health():
    """Health check endpoint that also advances cycle if needed"""
    try:
        run_cycle_tick()
    except Exception as e:
        current_app.logger.debug(f"tick_on_health_error: {e}")
    return "ok", 200

@cycle_bp.route('/status', methods=['GET'])
@cross_origin()
def get_cycle_status():
    """Get the current cycle status and timing information"""
    try:
        # Run cycle tick opportunistically
        try:
            run_cycle_tick()
        except Exception as e:
            current_app.logger.exception(f"cycle_tick_error: {e}")
        
        # Get current cycle
        cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
        
        # Print diagnostic info
        current_app.logger.info("--------- CYCLE STATUS CHECK ---------")
        
        if cycle:
            now = get_central_time()  # Use timezone-aware current time
            
            # Use matches_viewable_end from database
            viewing_period_end = cycle.matches_viewable_end
            
            # Log time info
            current_app.logger.info(f"Current time: {now}")
            current_app.logger.info(f"Survey end: {cycle.survey_end_date}")
            current_app.logger.info(f"Processing end: {cycle.processing_end_date}")
            current_app.logger.info(f"Viewing period end: {viewing_period_end}")
            
            # Time comparisons 
            current_app.logger.info(f"now < survey_end: {now < cycle.survey_end_date}")
            current_app.logger.info(f"now >= survey_end and now < processing_end: {now >= cycle.survey_end_date and now < cycle.processing_end_date}")
            current_app.logger.info(f"now >= processing_end and now < viewing_period_end: {now >= cycle.processing_end_date and now < viewing_period_end}")
            current_app.logger.info(f"Seconds until viewing_period_end: {(viewing_period_end - now).total_seconds() if viewing_period_end > now else 'past'}")
        else:
            current_app.logger.info("No active cycle found")
            
        # Get the cycle status
        cycle_status = check_cycle_status()
        
        # Log the status we're about to return
        if isinstance(cycle_status, dict):
            current_app.logger.info(f"Returning cycle status: {cycle_status['status']}, next phase: {cycle_status['next_phase']}")
            
            # Check if matches exist for debugging
            match_count = MatchModel.query.filter(MatchModel.cycle_id == cycle.id).count() if cycle else 0
            current_app.logger.info(f"Current match count for this cycle: {match_count}")
        else:
            current_app.logger.info(f"Returning cycle status (string): {cycle_status}")
        
        current_app.logger.info("--------- END CYCLE STATUS CHECK ---------")
        
        if isinstance(cycle_status, str):
            # Handle legacy string return from check_cycle_status
            return jsonify({
                "status": cycle_status,
                "cycle_number": 0,
                "survey_start_date": "",
                "survey_end_date": "",
                "processing_end_date": "",
                "time_remaining": 0,
                "next_phase": "",
                "next_phase_date": ""
            }), 200
        
        # We're returning all the cycle information directly from check_cycle_status
        return jsonify(cycle_status), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting cycle status: {str(e)}")
        return jsonify({"error": f"Error getting cycle status: {str(e)}"}), 500

@cycle_bp.route('/debug', methods=['GET'])
@cross_origin()
def debug_cycle():
    """Internal debugging endpoint"""
    return jsonify({"message": "Cycle system now runs fully automatically"}), 200

@cycle_bp.route('/admin/force-end', methods=['POST'])
@cross_origin()
def force_end_cycle():
    """Admin endpoint to force end current cycle"""
    try:
        # Verify admin secret
        admin_secret = request.headers.get('X-Admin-Secret')
        if not admin_secret or admin_secret != os.environ.get('ADMIN_SECRET'):
            return jsonify({"error": "Unauthorized"}), 401
            
        # Get current cycle
        cycle = MatchingCycle.query.filter_by(is_active=True).first()
        if not cycle:
            return jsonify({"error": "No active cycle"}), 404
            
        # Force end current cycle
        cycle.is_active = False
        db.session.commit()
        
        # Create new cycle
        from ..models.cycle import create_next_cycle
        new_cycle = create_next_cycle()
        
        return jsonify({
            "message": "Cycle ended successfully",
            "new_cycle": {
                "cycle_number": new_cycle.cycle_number,
                "survey_end_date": new_cycle.survey_end_date.strftime('%Y-%m-%d %H:%M:%S'),
                "processing_end_date": new_cycle.processing_end_date.strftime('%Y-%m-%d %H:%M:%S'),
                "is_production_cycle": new_cycle.is_production_cycle
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error in force end cycle: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_matches_with_descriptions():
    """Generate matches and add AI-generated descriptions for each match"""
    try:
        # Use relative imports
        from ..routes.matches import generate_matches_internal
        result = generate_matches_internal(force=False)
        
        # Add descriptions if matches were generated
        if result.get('status_code', 500) == 200 and result.get('match_count', 0) > 0:
            add_descriptions_to_matches()
            
        return result
    except Exception as e:
        current_app.logger.error(f"Error generating matches with descriptions: {str(e)}")
        return {"status_code": 500, "message": str(e)}

def generate_match_description(user1_email, user2_email):
    """Generate an AI description for a match between two users"""
    try:
        current_app.logger.info(f"Generating description for match: {user1_email} - {user2_email}")
        
        # Check if OpenAI API key is available
        if not openai.api_key:
            current_app.logger.warning("No OpenAI API key found. Using fallback description.")
            return generate_fallback_description()
            
        # Get the match to find its cycle_id
        match = MatchModel.query.filter(
            ((MatchModel.user1_email == user1_email) & (MatchModel.user2_email == user2_email)) |
            ((MatchModel.user1_email == user2_email) & (MatchModel.user2_email == user1_email))
        ).first()
        
        if not match:
            current_app.logger.warning(f"No match found for {user1_email} - {user2_email}")
            return generate_fallback_description()
            
        # Get user1's data
        user1_data = db.session.query(User, SurveyResponse.responses).join(
            SurveyResponse, User.id == SurveyResponse.user_id
        ).filter(
            User.email == user1_email,
            SurveyResponse.is_submitted == True,
            SurveyResponse.cycle_id == match.cycle_id  # Use cycle_id from the match
        ).first()
        
        # Get user2's data
        user2_data = db.session.query(User, SurveyResponse.responses).join(
            SurveyResponse, User.id == SurveyResponse.user_id
        ).filter(
            User.email == user2_email,
            SurveyResponse.is_submitted == True,
            SurveyResponse.cycle_id == match.cycle_id  # Use cycle_id from the match
        ).first()
        
        if not user1_data or not user2_data:
            current_app.logger.warning(f"Missing user data for {user1_email} or {user2_email}")
            return generate_fallback_description()
            
        try:
            # Import the format_survey_responses function directly
            import inspect
            import sys
            import os
            
            # Get file directory for relative imports
            current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
            parent_dir = os.path.dirname(current_dir)
            
            # Create a safer formatter function
            def format_responses_safely(answers_json):
                import json
                
                try:
                    # Parse answers
                    if isinstance(answers_json, dict):
                        answers = answers_json
                    else:
                        try:
                            answers = json.loads(answers_json)
                        except:
                            return "Error parsing responses"
                    
                    # Get SURVEY_QUESTIONS
                    from ..survey.surveyData import SURVEY_QUESTIONS
                    
                    # Create a lookup dictionary for questions
                    question_lookup = {}
                    for q in SURVEY_QUESTIONS:
                        if hasattr(q, 'id'):  # It's a Question object
                            q_id = str(q.id)
                            question_lookup[q_id] = {
                                'text': q.text,
                                'category': q.category
                            }
                        else:  # Dictionary case (shouldn't happen)
                            q_id = str(q['id'])
                            question_lookup[q_id] = {
                                'text': q['text'],
                                'category': q.get('category', '')
                            }
                    
                    # Format responses
                    formatted = []
                    for q_id, answer in answers.items():
                        if q_id in question_lookup:
                            q_text = question_lookup[q_id]['text']
                            formatted.append(f"{q_text}: {answer}")
                    
                    return "\n".join(formatted)
                except Exception as e:
                    return f"Error formatting responses: {str(e)}"
            
            # Format responses
            user1_responses = format_responses_safely(user1_data[1])
            user2_responses = format_responses_safely(user2_data[1])
            
            # Create prompt
            prompt = f"""
            Based on these two users' survey responses, generate a brief, friendly description of why they might be compatible.
            Focus on shared interests and complementary traits.
            
            User 1 responses:
            {user1_responses}
            
            User 2 responses:
            {user2_responses}
            
            Generate a 2-3 sentence description of their potential compatibility.
            """
            
            # Try calling OpenAI API
            try:
                current_app.logger.info("Attempting to call OpenAI API for description...")
                # Call OpenAI
                response = openai.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    messages=[
                        {"role": "system", "content": "You are a matchmaker helping people understand their potential matches."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=120,  # Reduced from 16384 to 120 for short descriptions
                    temperature=0.7
                )
                
                description = response.choices[0].message.content.strip()
                current_app.logger.info(f"OpenAI response for description: {description}")
                return description
            except Exception as openai_error:
                # OpenAI error (likely quota), use fallback
                current_app.logger.error(f"OpenAI API error in description generation: {openai_error}")
                return generate_fallback_description()
        except Exception as format_error:
            current_app.logger.error(f"Error formatting responses for description: {format_error}")
            return generate_fallback_description()
            
    except Exception as e:
        current_app.logger.error(f"Error generating match description: {e}")
        return generate_fallback_description()

def generate_fallback_description():
    """Generate a generic fallback description when OpenAI API fails"""
    import random
    
    descriptions = [
        "A thoughtful and engaging individual who values meaningful connections and shared experiences. They bring a unique perspective and warmth to relationships.",
        
        "Someone with diverse interests and a positive outlook on life. They're looking for authentic connections based on mutual respect and shared values.",
        
        "A dynamic person who balances intellectual curiosity with emotional intelligence. They're passionate about growth and building genuine relationships.",
        
        "An interesting individual with a blend of creative and analytical qualities. They value honesty and enjoy both deep conversations and lighthearted fun.",
        
        "A well-rounded person who appreciates both adventure and quiet moments. They bring thoughtfulness and enthusiasm to their relationships.",
        
        "Someone who combines intelligence with empathy, making them a great conversationalist. They value authenticity and are looking for a meaningful connection.",
        
        "A balanced individual who values both independence and connection. They bring curiosity and warmth to their relationships and appreciate the same in others.",
        
        "An insightful person who approaches life with both passion and practicality. They value genuine connections and shared growth."
    ]
    
    return random.choice(descriptions)

def add_descriptions_to_matches():
    """Add descriptions to all matches that don't have them"""
    try:
        # Get all matches without descriptions
        matches = MatchModel.query.filter(MatchModel.description.is_(None)).all()
        
        if not matches:
            current_app.logger.info("No matches need descriptions")
            return  # No matches need descriptions
            
        current_app.logger.info(f"Adding descriptions to {len(matches)} matches")
        success_count = 0
        
        for match in matches:
            try:
                # Use fallback description
                description = generate_fallback_description()
                match.description = description
                success_count += 1
            except Exception as match_error:
                current_app.logger.error(f"Error processing match {match.id}: {match_error}")
        
        # Commit all description updates
        db.session.commit()
        current_app.logger.info(f"Successfully added descriptions to {success_count} matches")
        
    except Exception as e:
        current_app.logger.error(f"Error adding descriptions to matches: {e}")
        db.session.rollback() 