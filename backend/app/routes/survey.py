from flask import Blueprint, request, jsonify, current_app, g
from flask_cors import cross_origin
from datetime import datetime, timezone
from sqlalchemy import desc, and_
from .. import db
from ..models.models import User, SurveyResponse, MatchingCycle
from ..utils.auth import auth_required
from ..utils.csrf import csrf_protect

survey = Blueprint('survey', __name__)

def get_active_cycle():
    """Helper to get active cycle with error handling"""
    active_cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
    if not active_cycle:
        raise ValueError("No active matching cycle found")
    return active_cycle

@survey.route('/check', methods=['GET'])
@cross_origin()
def check_survey():
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({'message': 'Email is required', 'hasCompletedSurvey': False}), 400
            
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'message': 'User not found', 'hasCompletedSurvey': False}), 404
            
        try:
            active_cycle = get_active_cycle()
        except ValueError as e:
            return jsonify({'message': str(e), 'hasCompletedSurvey': False}), 500
            
        # Check if user has completed a survey for this cycle
        completed_survey = SurveyResponse.query.filter_by(
            user_id=user.id,
            is_submitted=True,
            cycle_id=active_cycle.id
        ).first()
        
        return jsonify({
            'hasCompletedSurvey': completed_survey is not None
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Survey status check error: {str(e)}")
        return jsonify({'message': f'Failed to check survey status: {str(e)}', 'hasCompletedSurvey': False}), 500

@survey.route('/progress', methods=['POST'])
@cross_origin()
def save_progress():
    """Save survey progress without submitting"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
            
        email = data.get('email')
        if not email:
            return jsonify({'message': 'Email is required'}), 400
            
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        try:
            active_cycle = get_active_cycle()
        except ValueError as e:
            return jsonify({'message': str(e)}), 500
            
        # Mark any existing progress as not latest
        SurveyResponse.query.filter(
            and_(
                SurveyResponse.user_id == user.id,
                SurveyResponse.cycle_id == active_cycle.id,
                SurveyResponse.is_submitted == False,
                SurveyResponse.is_latest_progress == True
            )
        ).update({'is_latest_progress': False})
        
        survey_data = {
            'stage': data.get('stage'),
            'currentQuestionIndex': data.get('currentQuestionIndex', 0),
            'answers': data.get('answers', {}),
            'noPreferenceChecked': data.get('noPreferenceChecked', {}),
            'checkboxStates': data.get('checkboxStates', {}),
            'name': data.get('name', '')
        }
        
        # Create new progress record
        new_survey = SurveyResponse(
            user_id=user.id,
            responses=survey_data,
            is_submitted=False,
            is_latest_progress=True,
            looking_for='opposite',  # TODO: derive from user.gender / orientation
            contact_info={'email': user.email},
            cycle_id=active_cycle.id
        )
        db.session.add(new_survey)
        db.session.commit()
        
        return jsonify({
            'message': 'Progress saved successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Progress save error: {str(e)}")
        db.session.rollback()
        return jsonify({'message': f'Failed to save progress: {str(e)}'}), 500

@survey.route('/progress', methods=['GET'])
@cross_origin()
def get_progress():
    """Get saved survey progress"""
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({'message': 'Email is required', 'hasProgress': False}), 400
            
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'message': 'User not found', 'hasProgress': False}), 404
            
        try:
            active_cycle = get_active_cycle()
        except ValueError as e:
            return jsonify({'message': str(e), 'hasProgress': False}), 500
            
        # Check for latest incomplete survey in current cycle
        incomplete_survey = SurveyResponse.query.filter(
            and_(
                SurveyResponse.user_id == user.id,
                SurveyResponse.cycle_id == active_cycle.id,
                SurveyResponse.is_submitted == False,
                SurveyResponse.is_latest_progress == True
            )
        ).first()
        
        if incomplete_survey and incomplete_survey.responses:
            return jsonify({
                'hasProgress': True,
                'progress': incomplete_survey.responses
            }), 200
        else:
            return jsonify({
                'hasProgress': False
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Progress retrieval error: {str(e)}")
        return jsonify({'message': f'Failed to retrieve progress: {str(e)}', 'hasProgress': False}), 500

@survey.route('/submit', methods=['POST'])
@cross_origin(origins=[
    "https://wucupid.com",
    "https://www.wucupid.com",
    "http://localhost:3000"
], supports_credentials=True)
@auth_required
@csrf_protect
def submit_survey():
    try:
        data = request.get_json()
        if not data or 'answers' not in data:
            return jsonify({'message': 'No survey data provided'}), 400
            
        # Derive user from authenticated session
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return jsonify({'message': 'Authentication required'}), 401
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        try:
            active_cycle = get_active_cycle()
        except ValueError as e:
            return jsonify({'message': str(e)}), 500
            
        current_app.logger.info(f"Processing survey for user_id: {user_id}")

        # Check if user already has a submitted survey for this cycle
        existing_submitted = SurveyResponse.query.filter_by(
            user_id=user.id,
            is_submitted=True,
            cycle_id=active_cycle.id
        ).first()
        
        if existing_submitted:
            return jsonify({
                'message': 'You have already submitted a survey for this cycle',
                'survey_id': existing_submitted.id
            }), 400
            
        # Process filter data if provided
        filter_data = data.get('filters', {})
        if filter_data:
            # Update user profile with filter data
            user.name = filter_data.get('name')
            user.instagram_handle = filter_data.get('instagram_handle')
            
            # Parse gender value with validation
            gender_value = filter_data.get('gender')
            valid_gender_values = {1: 'Male', 2: 'Female', 3: 'Non-binary'}
            user.gender = valid_gender_values.get(gender_value)
            
            # Parse academic year with validation
            year_value = filter_data.get('academic_year')
            valid_years = {1: 'Freshman', 2: 'Sophomore', 3: 'Junior', 4: 'Senior'}
            user.academic_year = valid_years.get(year_value)
            
            # Store preferred academic years
            if filter_data.get('preferred_years') == "no preference":
                user.preferred_years = ["no preference"]
            else:
                user.preferred_years = [
                    valid_years.get(year) for year in filter_data.get('preferred_years', [])
                    if year in valid_years
                ]
            
            # Parse religion with validation
            religion_value = filter_data.get('religion')
            valid_religions = {
                1: 'Christianity', 2: 'Islam', 3: 'Judaism',
                4: 'Atheism', 5: 'Other'
            }
            user.religion = valid_religions.get(religion_value)
            
            # Store preferred religions
            if filter_data.get('preferred_religions') == "no preference":
                user.preferred_religions = ["no preference"]
            else:
                user.preferred_religions = [
                    valid_religions.get(rel) for rel in filter_data.get('preferred_religions', [])
                    if rel in valid_religions
                ]
            
            # Parse political view with validation
            political_value = filter_data.get('political_view')
            valid_politics = {
                -2: 'Conservative', -1: 'Somewhat conservative',
                0: 'Neutral', 1: 'Somewhat Liberal', 2: 'Liberal'
            }
            user.political_view = valid_politics.get(political_value)
            
            # Store preferred political views
            if filter_data.get('preferred_political_views') == "no preference":
                user.preferred_political_views = ["no preference"]
            else:
                user.preferred_political_views = [
                    valid_politics.get(pol) for pol in filter_data.get('preferred_political_views', [])
                    if pol in valid_politics
                ]
            
            # Parse sexual orientation with validation
            orientation_value = filter_data.get('sexual_orientation')
            valid_orientations = {1: 'Men', 2: 'Women', 3: 'Everyone'}
            user.sexual_orientation = valid_orientations.get(orientation_value)
            
            db.session.add(user)
        
        # Mark any existing progress as not latest
        SurveyResponse.query.filter(
            and_(
                SurveyResponse.user_id == user.id,
                SurveyResponse.cycle_id == active_cycle.id,
                SurveyResponse.is_submitted == False,
                SurveyResponse.is_latest_progress == True
            )
        ).update({'is_latest_progress': False})
        
        # Create a new survey record
        new_survey = SurveyResponse(
            user_id=user.id,
            responses=data['answers'],
            is_submitted=True,
            is_latest_progress=False,  # Submitted surveys are never latest progress
            submitted_at=datetime.now(timezone.utc),
            looking_for='opposite',  # TODO: derive from user.gender / orientation
            contact_info={'email': user.email},
            cycle_id=active_cycle.id
        )
        
        db.session.add(new_survey)
        db.session.commit()
        
        # Add structured log for analytics
        current_app.logger.info(f"survey_submit user={user.id} cycle={active_cycle.id}")
        
        return jsonify({
            'message': 'Survey submitted successfully',
            'survey_id': new_survey.id
        }), 201
    
    except Exception as e:
        current_app.logger.error(f"Survey submission error: {str(e)}")
        db.session.rollback()
        return jsonify({'message': f'Survey submission failed: {str(e)}'}), 500
