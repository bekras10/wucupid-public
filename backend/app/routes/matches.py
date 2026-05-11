from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
import json
import numpy as np
from datetime import datetime, timezone
from sqlalchemy import desc
import os
import random
from .. import db
from ..models.models import MatchingCycle  # Isolated import
from ..models.models import (
    User, 
    SurveyResponse, 
    Match, 
    MatchingAttempt
)
from ..models.cycle import check_cycle_status, get_central_time
from ..survey.surveyData import SURVEY_QUESTIONS

# Create a Blueprint for the matches routes
matches_bp = Blueprint('matches', __name__)

# Constants for vector-based matching
WEIGHT_RELIGION = 3.0
WEIGHT_POLITICS = 2.0
WEIGHT_YEAR = 1.5
WEIGHT_PERSONALITY = 1.0  # base weight for survey block; scaled dynamically by length
NEGATIVE_TOLERANCE = 0.02  # allow small negatives to be considered for soft-filter rescue

class UserMatchingData:
    """Data structure to hold user information for vector-based matching"""
    def __init__(self, email, survey_responses, gender, academic_year, religion, 
                 political_view, sexual_orientation, preferred_years=None, 
                 preferred_religions=None, preferred_political_views=None):
        self.email = email
        self.gender = gender
        self.academic_year = academic_year
        self.religion = religion
        self.political_view = political_view
        self.sexual_orientation = sexual_orientation
        self.preferred_years = preferred_years or []
        self.preferred_religions = preferred_religions or []
        self.preferred_political_views = preferred_political_views or []
        
        # Convert survey responses to vector
        self.survey_vector = self._build_survey_vector(survey_responses)
        self.soft_filter_vector = self._build_soft_filter_vector()
        
        # Combine and normalize
        self.full_vector = self._build_full_vector()
        
        # Gender and orientation indices for compatibility checking
        self.gender_idx = self._get_gender_idx()
        self.orientation_mask = self._get_orientation_mask()
    
    def _build_survey_vector(self, survey_responses):
        """Convert survey responses to vector of scores -2 to +2 using dynamic length and reverse flags from SURVEY_QUESTIONS"""
        total_questions = len(SURVEY_QUESTIONS)
        vector = np.zeros(total_questions, dtype=np.int8)
        
        if not survey_responses:
            return vector
            
        # Handle both dict and JSON string formats
        if isinstance(survey_responses, str):
            try:
                responses = json.loads(survey_responses)
            except:
                return vector
        else:
            responses = survey_responses
            
        # Build reverse-scored ID set from survey definition
        reverse_ids = {q.id for q in SURVEY_QUESTIONS if getattr(q, 'reverse', False)}

        # Map question IDs 1..N to vector indices 0..N-1
        for q_id, answer_value in responses.items():
            try:
                q_idx = int(q_id) - 1  # Convert to 0-based index
                if 0 <= q_idx < total_questions:
                    # Handle reverse-scored questions using reverse_ids set
                    if (q_idx + 1) in reverse_ids:
                        vector[q_idx] = -int(answer_value)
                    else:
                        vector[q_idx] = int(answer_value)
            except (ValueError, TypeError):
                continue
                
        return vector
    
    def _build_soft_filter_vector(self):
        """Build one-hot encoded vectors for soft filters"""
        # Academic year one-hot (4 dimensions)
        year_vector = np.zeros(4, dtype=np.float32)
        if self.academic_year:
            year_map = {"Freshman": 0, "Sophomore": 1, "Junior": 2, "Senior": 3}
            idx = year_map.get(self.academic_year)
            if idx is not None:
                year_vector[idx] = 1.0
        
        # Religion one-hot (5 dimensions)
        religion_vector = np.zeros(5, dtype=np.float32)
        if self.religion:
            religion_map = {"Christianity": 0, "Islam": 1, "Judaism": 2, "Atheism": 3, "Other": 4}
            idx = religion_map.get(self.religion)
            if idx is not None:
                religion_vector[idx] = 1.0
        
        # Political view one-hot (5 dimensions) - but use the actual scale
        politics_vector = np.zeros(5, dtype=np.float32)
        if self.political_view:
            politics_map = {"Conservative": 0, "Somewhat conservative": 1, 
                          "Neutral": 2, "Somewhat Liberal": 3, "Liberal": 4}
            idx = politics_map.get(self.political_view)
            if idx is not None:
                politics_vector[idx] = 1.0
        
        return np.concatenate([year_vector, religion_vector, politics_vector])
    
    def _build_full_vector(self):
        """Combine survey and soft filter vectors with weights"""
        # Apply weights to different components
        # Dynamically scale survey weight to preserve historical balance as question count changes
        # Previous baseline length was 38
        baseline_len = 38.0
        current_len = float(len(self.survey_vector)) if len(self.survey_vector) > 0 else baseline_len
        dynamic_personality_weight = WEIGHT_PERSONALITY * np.sqrt(baseline_len / current_len)
        weighted_survey = self.survey_vector.astype(np.float32) * dynamic_personality_weight
        weighted_soft = self.soft_filter_vector.copy()
        
        # Apply specific weights to soft filter components
        weighted_soft[0:4] *= WEIGHT_YEAR      # Academic year
        weighted_soft[4:9] *= WEIGHT_RELIGION  # Religion  
        weighted_soft[9:14] *= WEIGHT_POLITICS # Politics
        
        # Combine vectors
        full_vec = np.concatenate([weighted_survey, weighted_soft])
        
        # L2 normalize
        norm = np.linalg.norm(full_vec)
        if norm > 0:
            full_vec = full_vec / norm
            
        return full_vec
    
    def _get_gender_idx(self):
        """Convert gender to index: 0=Male, 1=Female, 2=Non-binary"""
        gender_map = {"male": 0, "female": 1, "non-binary": 2}
        return gender_map.get(self.gender.lower() if self.gender else "", 0)
    
    def _get_orientation_mask(self):
        """Create mask for compatible genders: [can_date_males, can_date_females, can_date_nonbinary]"""
        # Handle None/empty values explicitly
        if not self.sexual_orientation:
            # Log for debugging - this probably means the user didn't complete the survey properly
            print(f"DEBUG: User {self.email} has empty/null sexual orientation")
            return np.array([False, False, False])
            
        orientation = self.sexual_orientation.strip().lower()
        
        # Handle the three expected database values
        if orientation == "men":
            return np.array([True, False, False])
        elif orientation == "women":
            return np.array([False, True, False])
        elif orientation == "everyone":
            return np.array([True, True, True])
        
        # Extended support for other common variants (just in case)
        if any(term in orientation for term in ["bisexual", "bi", "pansexual", "pan", "both", "all"]):
            return np.array([True, True, True])
        
        # Only interested in non-binary people
        if any(term in orientation for term in ["non-binary", "nonbinary", "nb", "enby"]) and "men" not in orientation and "women" not in orientation:
            return np.array([False, False, True])
        
        # Log unrecognized values for debugging
        print(f"DEBUG: User {self.email} has unrecognized sexual orientation: '{self.sexual_orientation}'")
        return np.array([False, False, False])

def build_compatibility_matrix(users):
    """Build matrices for fast vector-based matching"""
    n = len(users)
    current_app.logger.info(f"Building compatibility matrix for {n} users")
    
    # Build user vector matrix
    V = np.vstack([user.full_vector for user in users])  # Shape: (n, 52)
    
    # Gender and orientation arrays
    G = np.array([user.gender_idx for user in users])  # Shape: (n,)
    SO = np.vstack([user.orientation_mask for user in users])  # Shape: (n, 3)
    
    # Log gender and orientation info
    # current_app.logger.info("Gender indices: " + str(G))
    # current_app.logger.info("Orientation masks:")
    # for i, user in enumerate(users):
    #     current_app.logger.info(f"  User {i} ({user.email}): gender_idx={G[i]}, mask={SO[i]}")
    
    # Sexual orientation compatibility matrix
    # SO @ (G == np.arange(3)).T gives us which users each user can date
    gender_matrix = (G[:, None] == np.arange(3)).T  # Shape: (3, n)
    can_date_bool = (SO @ gender_matrix) > 0  # Shape: (n, n) boolean mask
    
    # Log the can_date matrix (disabled for verbosity in production)
    # current_app.logger.info("Can date matrix:")
    # for i in range(n):
    #     for j in range(n):
    #         if can_date_bool[i, j]:
    #             current_app.logger.info(f"  User {i} ({users[i].email}) can date User {j} ({users[j].email})")
    
    # Mutual compatibility (both users must be able to date each other)
    compatibility = can_date_bool & can_date_bool.T
    
    # Log mutual compatibility
    compatible_pairs = []
    for i in range(n):
        for j in range(i+1, n):  # Only check upper triangle
            if compatibility[i, j]:
                compatible_pairs.append((i, j))
                # Detailed per-pair mutual compatibility logging disabled for verbosity
    
    current_app.logger.info(f"Total compatible pairs found: {len(compatible_pairs)}")
    
    # Cosine similarity matrix (already normalized vectors, so just dot product)
    similarity = V @ V.T  # Shape: (n, n)
    
    # Apply compatibility mask (set incompatible pairs to -1)
    similarity[~compatibility] = -1.0
    
    # Zero out diagonal (no self-matches)  
    np.fill_diagonal(similarity, -1.0)
    
    # Log how many positive similarities remain
    positive_similarities = np.sum(similarity > 0)
    current_app.logger.info(f"Positive similarity scores after compatibility filtering: {positive_similarities}")
    
    return similarity

def apply_soft_filter_preferences(users, similarity_matrix):
    """Apply soft filter preferences as additional scoring (symmetric)"""
    n = len(users)
    
    for i in range(n):
        user = users[i]
        
        for j in range(i+1, n):  # Only process upper triangle to avoid double application
            # Skip pairs that are fundamentally incompatible (exactly masked to -1.0)
            if similarity_matrix[i, j] <= -0.999:
                continue
                
            other_user = users[j]
            
            # Calculate preference bonus for i->j direction
            preference_bonus_i_to_j = 0.0
            
            # Academic year preferences (i's preferences about j)
            if user.preferred_years and "no preference" not in user.preferred_years:
                if other_user.academic_year in user.preferred_years:
                    preference_bonus_i_to_j += 0.1
                else:
                    preference_bonus_i_to_j -= 0.05
                    
            # Religion preferences (i's preferences about j)
            if user.preferred_religions and "no preference" not in user.preferred_religions:
                if other_user.religion in user.preferred_religions:
                    preference_bonus_i_to_j += 0.15
                else:
                    preference_bonus_i_to_j -= 0.1
                    
            # Political preferences (i's preferences about j)
            if user.preferred_political_views and "no preference" not in user.preferred_political_views:
                if other_user.political_view in user.preferred_political_views:
                    preference_bonus_i_to_j += 0.1
                else:
                    preference_bonus_i_to_j -= 0.05
            
            # Calculate preference bonus for j->i direction
            preference_bonus_j_to_i = 0.0
            
            # Academic year preferences (j's preferences about i)
            if other_user.preferred_years and "no preference" not in other_user.preferred_years:
                if user.academic_year in other_user.preferred_years:
                    preference_bonus_j_to_i += 0.1
                else:
                    preference_bonus_j_to_i -= 0.05
                    
            # Religion preferences (j's preferences about i)
            if other_user.preferred_religions and "no preference" not in other_user.preferred_religions:
                if user.religion in other_user.preferred_religions:
                    preference_bonus_j_to_i += 0.15
                else:
                    preference_bonus_j_to_i -= 0.1
                    
            # Political preferences (j's preferences about i)
            if other_user.preferred_political_views and "no preference" not in other_user.preferred_political_views:
                if user.political_view in other_user.preferred_political_views:
                    preference_bonus_j_to_i += 0.1
                else:
                    preference_bonus_j_to_i -= 0.05
                    
            # Apply bonuses/penalties symmetrically
            similarity_matrix[i, j] = min(1.0, similarity_matrix[i, j] + preference_bonus_i_to_j)
            similarity_matrix[j, i] = min(1.0, similarity_matrix[j, i] + preference_bonus_j_to_i)
    
    return similarity_matrix

def generate_matches_from_similarity_matrix(users, similarity_matrix, k=3):
    """Generate matches from similarity matrix using mutual top-k selection"""
    # Get the active cycle first
    cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
    if not cycle:
        current_app.logger.error("No active cycle when generating matches")
        return []

    n = len(users)
    
    # Get top-k matches for each user
    topk = []
    for i in range(n):
        # Allow slightly negative values to be rescued by bonuses; threshold controlled by NEGATIVE_TOLERANCE
        valid = np.where(similarity_matrix[i] > -NEGATIVE_TOLERANCE)[0]
        if valid.size:
            kth = min(k, valid.size) - 1
            idx = valid[np.argpartition(-similarity_matrix[i, valid], kth)[:kth+1]]
            topk.append(set(idx))
        else:
            topk.append(set())
    
    # Create matches only for mutual top-k pairs
    # Use a dictionary to deduplicate matches
    unique_matches = {}  # (user1_email, user2_email) -> match_data
    
    for i in range(n):
        for j in topk[i]:
            if i in topk[j]:  # Mutual top-k only
                # Get emails and ensure consistent ordering
                email1, email2 = users[i].email, users[j].email
                # Always sort emails to ensure consistent ordering
                email1, email2 = sorted([email1, email2])
                
                # Create unique key for this pair
                pair_key = (email1, email2)
                
                # Skip if we've already processed this pair
                if pair_key in unique_matches:
                    continue
                
                # Use average score for fairness (since soft filters are asymmetric)
                avg_score = 0.5 * (similarity_matrix[i, j] + similarity_matrix[j, i])
                
                unique_matches[pair_key] = {
                    'user1_email': email1,
                    'user2_email': email2,
                    'score': float(avg_score),
                    'date_created': get_central_time(),
                    'cycle_id': cycle.id
                }
    
    # Convert dictionary values to list
    matches = list(unique_matches.values())
    current_app.logger.info(f"Generated {len(matches)} unique matches after deduplication")
    
    return matches

@matches_bp.route('/generate', methods=['POST'])
@cross_origin()
def generate_matches():
    """Generate matches for all users who have completed the survey."""
    try:
        # Check if we're in the processing phase
        cycle_status = check_cycle_status()
        
        # Determine if we can proceed with match generation
        if isinstance(cycle_status, dict) and cycle_status.get("status") != "processing":
            return jsonify({
                "message": f"Match generation is only allowed during the processing phase. Current phase: {cycle_status.get('status', 'unknown')}",
                "match_count": 0
            }), 400
            
        # Log the attempt
        current_app.logger.info("Manual match generation requested via API")
        
        # This now calls the internal function instead of implementing match logic here
        result = generate_matches_internal(force=True)
        return jsonify({
            "message": result.get("message", "Unknown error"),
            "match_count": result.get("match_count", 0)
        }), result.get("status_code", 500)
        
    except Exception as e:
        current_app.logger.error(f"Error generating matches: {str(e)}")
        return jsonify({"message": f"Error generating matches: {str(e)}"}), 500



def generate_matches_internal(force=False):
    """Generate matches using fast vector-based algorithm (for internal use)
    
    Args:
        force (bool): If True, will generate matches even if there's already an attempt for this cycle
                     or if we're in matches_available phase (for recovery)
    """
    try:
        current_app.logger.info(f"Starting match generation with force={force}")
        
        # Check if we're in the processing phase
        cycle_status = check_cycle_status()
        if cycle_status["status"] != "processing" and not force:
            current_app.logger.warning(f"Attempted to generate matches outside of processing phase. Current phase: {cycle_status['status']}")
            return {"message": "Match generation is only allowed during the processing phase", "status_code": 400}
        
        # Get the active cycle
        cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
        
        if not cycle:
            current_app.logger.error("No active cycle found")
            return {"message": "No active cycle found", "status_code": 400}

        # Load users with survey responses
        users_with_responses = db.session.query(
            User.email, 
            SurveyResponse.responses, 
            User.gender,
            User.academic_year,
            User.preferred_years,
            User.religion,
            User.preferred_religions,
            User.political_view,
            User.preferred_political_views,
            User.sexual_orientation
        ).join(
            SurveyResponse, User.id == SurveyResponse.user_id
        ).filter(
            SurveyResponse.is_submitted == True,
            SurveyResponse.cycle_id == cycle.id,  # Only use responses from current cycle
            SurveyResponse.submitted_at.between(cycle.survey_start_date, cycle.survey_end_date)  # Double-check submission timing
        ).all()
        
        current_app.logger.info(
            f"Found {len(users_with_responses)} users with valid survey responses for cycle #{cycle.id} "
            f"(submitted between {cycle.survey_start_date} and {cycle.survey_end_date})"
        )

        if len(users_with_responses) < 2:
            current_app.logger.info("Not enough users have completed the survey")
            create_or_update_matching_attempt(cycle.id, False)
            return {"message": "Not enough users have completed the survey", "status_code": 400}
        
        # Convert to UserMatchingData objects
        users = []
        for user_data in users_with_responses:
            try:
                user_obj = UserMatchingData(
                    email=user_data.email,
                    survey_responses=user_data.responses,
                    gender=user_data.gender,
                    academic_year=user_data.academic_year,
                    religion=user_data.religion,
                    political_view=user_data.political_view,
                    sexual_orientation=user_data.sexual_orientation,
                    preferred_years=user_data.preferred_years,
                    preferred_religions=user_data.preferred_religions,
                    preferred_political_views=user_data.preferred_political_views
                )
                
                # Validate that user has critical data for matching
                missing_data = []
                if user_obj.survey_vector is None:
                    missing_data.append("survey responses")
                if not user_obj.gender:
                    missing_data.append("gender")
                if not user_obj.sexual_orientation:
                    missing_data.append("sexual orientation")
                
                if missing_data:
                    current_app.logger.warning(f"User {user_data.email} missing critical data: {', '.join(missing_data)} - skipping")
                    continue
                    
                users.append(user_obj)
            except Exception as user_error:
                current_app.logger.error(f"Error processing user {user_data.email}: {str(user_error)}")
                continue
        
        # Drop users with unusable orientation masks
        initial_user_count = len(users)
        users = [u for u in users if u.orientation_mask.any()]
        filtered_user_count = len(users)
        
        if len(users) < 2:
            current_app.logger.info("Not enough valid users for matching after filtering")
            create_or_update_matching_attempt(cycle.id, False)
            return {"message": "Not enough valid users for matching", "status_code": 400}
            
        current_app.logger.info(f"Processing {len(users)} valid users with vector-based matching")
        
        # Build compatibility and similarity matrices
        similarity_matrix = build_compatibility_matrix(users)
        
        # Apply soft filter preferences
        similarity_matrix = apply_soft_filter_preferences(users, similarity_matrix)
        
        # Generate matches from similarity matrix
        matches = generate_matches_from_similarity_matrix(users, similarity_matrix, k=3)
        
        if not matches:
            current_app.logger.info("No compatible matches found")
            create_or_update_matching_attempt(cycle.id, False)
            return {
                "message": "No compatible matches could be calculated.",
                "status_code": 400
            }
        
        # Start a transaction for the combined process
        try:
            # Insert new matches
            created_matches = []
            
            # Use ON CONFLICT DO NOTHING as a safety net
            from sqlalchemy.dialects.postgresql import insert
            for match_data in matches:
                stmt = insert(Match).values(
                    user1_email=match_data['user1_email'],
                    user2_email=match_data['user2_email'],
                    score=match_data['score'],
                    date_created=match_data['date_created'],
                    cycle_id=cycle.id
                ).on_conflict_do_nothing(
                    index_elements=['cycle_id', 'user1_email', 'user2_email']
                )
                result = db.session.execute(stmt)
                if result.rowcount > 0:
                    match = Match(
                        user1_email=match_data['user1_email'],
                        user2_email=match_data['user2_email'],
                        score=match_data['score'],
                        date_created=match_data['date_created'],
                        cycle_id=cycle.id
                    )
                    created_matches.append(match)
            
            # Flush to get IDs but don't commit yet
            db.session.flush()
            
            # Add descriptions to matches
            for match in created_matches:
                try:
                    from ..routes.cycle import generate_fallback_description
                    description = generate_fallback_description()
                    match.description = description
                except Exception as match_error:
                    current_app.logger.error(f"Error adding description to match {match.id}: {str(match_error)}")
                    match.description = "A compatible match based on your preferences and interests."
            
            # Optional filler matches to ensure near-universal coverage for unmatched users
            # Feature flag: ENABLE_FILLER_MATCHES ("1", "true", "yes") enables this block
            try:
                enable_filler = str(os.environ.get("ENABLE_FILLER_MATCHES", "")).strip().lower() in ("1", "true", "yes")
                if enable_filler:
                    filler_created_total = 0
                    # Build quick lookup helpers
                    email_to_index = {u.email: idx for idx, u in enumerate(users)}
                    index_to_email = {idx: u.email for idx, u in enumerate(users)}
                    n_users = len(users)
                    
                    # Fetch existing pairs and counts for this cycle (includes rows inserted above within this tx)
                    existing_pairs = set()
                    match_count_by_email = {}
                    cycle_matches = Match.query.filter(Match.cycle_id == cycle.id).all()
                    for m in cycle_matches:
                        if not m.user1_email or not m.user2_email:
                            continue
                        a, b = sorted([m.user1_email, m.user2_email])
                        existing_pairs.add((a, b))
                        match_count_by_email[a] = match_count_by_email.get(a, 0) + 1
                        match_count_by_email[b] = match_count_by_email.get(b, 0) + 1
                    
                    # Determine unmatched users (zero matches so far in this cycle)
                    unmatched_indices = [i for i in range(n_users) if match_count_by_email.get(index_to_email[i], 0) == 0]
                    random.shuffle(unmatched_indices)
                    
                    # Precompute compatibility (mutual gender/orientation only): similarity > -1.0 indicates compatible
                    def compatible(i, j):
                        return i != j and similarity_matrix[i, j] > -1.0
                    
                    filler_created = 0
                    from sqlalchemy.dialects.postgresql import insert as pg_insert
                    now_ct = get_central_time()
                    
                    # 1) Pass: unmatched-with-unmatched
                    still_unmatched = set(unmatched_indices)
                    for i in list(still_unmatched):
                        if i not in still_unmatched:
                            continue
                        candidates = [j for j in still_unmatched if compatible(i, j)]
                        if not candidates:
                            continue
                        j = random.choice(candidates)
                        email_i = index_to_email[i]
                        email_j = index_to_email[j]
                        a, b = sorted([email_i, email_j])
                        if (a, b) in existing_pairs:
                            # Already paired in this cycle
                            still_unmatched.discard(i)
                            still_unmatched.discard(j)
                            continue
                        filler_score = 0.10 + random.random() * 0.15
                        stmt = pg_insert(Match).values(
                            user1_email=a,
                            user2_email=b,
                            score=float(filler_score),
                            date_created=now_ct,
                            cycle_id=cycle.id
                        ).on_conflict_do_nothing(
                            index_elements=['cycle_id', 'user1_email', 'user2_email']
                        )
                        res = db.session.execute(stmt)
                        if res.rowcount > 0:
                            filler_created += 1
                            existing_pairs.add((a, b))
                            match_count_by_email[a] = match_count_by_email.get(a, 0) + 1
                            match_count_by_email[b] = match_count_by_email.get(b, 0) + 1
                            still_unmatched.discard(i)
                            still_unmatched.discard(j)
                    
                    # 2) Fallback pass: remaining unmatched vs any compatible user (including matched)
                    for i in list(still_unmatched):
                        email_i = index_to_email[i]
                        # Build candidate list among all users
                        candidates = [j for j in range(n_users) if compatible(i, j)]
                        # Exclude pairs already existing
                        filtered = []
                        for j in candidates:
                            email_j = index_to_email[j]
                            a, b = sorted([email_i, email_j])
                            if (a, b) not in existing_pairs:
                                filtered.append(j)
                        if not filtered:
                            continue
                        j = random.choice(filtered)
                        email_j = index_to_email[j]
                        a, b = sorted([email_i, email_j])
                        filler_score = 0.10 + random.random() * 0.15
                        stmt = pg_insert(Match).values(
                            user1_email=a,
                            user2_email=b,
                            score=float(filler_score),
                            date_created=now_ct,
                            cycle_id=cycle.id
                        ).on_conflict_do_nothing(
                            index_elements=['cycle_id', 'user1_email', 'user2_email']
                        )
                        res = db.session.execute(stmt)
                        if res.rowcount > 0:
                            filler_created += 1
                            existing_pairs.add((a, b))
                            match_count_by_email[a] = match_count_by_email.get(a, 0) + 1
                            match_count_by_email[b] = match_count_by_email.get(b, 0) + 1
                    
                    current_app.logger.info(f"filler_matches_created count={filler_created}")
                    filler_created_total = filler_created
            except Exception as filler_error:
                # Do not fail the transaction if filler creation encounters an error
                current_app.logger.error(f"filler_matches_error: {str(filler_error)}")

            # Record successful matching attempt
            create_or_update_matching_attempt(cycle.id, True)
                
            # Now commit everything at once
            db.session.commit()
            
            # Report total created including filler (if any)
            try:
                total_filler = locals().get('filler_created_total', 0) or 0
            except Exception:
                total_filler = 0
            match_count = len(created_matches) + total_filler
            if total_filler:
                current_app.logger.info(f"Generated {match_count} matches (including {total_filler} filler)")
            else:
                current_app.logger.info(f"Generated {match_count} matches using vector-based algorithm")
            
            return {
                "message": "Matches generated successfully",
                "match_count": match_count,
                "status_code": 200
            }
        
        except Exception as tx_error:
            db.session.rollback()
            current_app.logger.error(f"Error in match generation transaction: {str(tx_error)}")
            create_or_update_matching_attempt(cycle.id, False)
            return {"message": f"Error generating matches: {str(tx_error)}", "status_code": 500}
        
    except Exception as e:
        current_app.logger.error(f"Error generating matches: {str(e)}")
        try:
            db.session.rollback()
            create_or_update_matching_attempt(cycle.id, False)
        except Exception as record_error:
            db.session.rollback()
            current_app.logger.error(f"Failed to record matching attempt: {str(record_error)}")
            
        return {"message": f"Error generating matches: {str(e)}", "status_code": 500}

def get_user_matches_internal(email):
    """
    Internal function to get matches for a user.
    Returns list of matches with shared filter tags.
    """
    try:
        # Check if we're in the matches_available phase
        cycle_status = check_cycle_status()
        if cycle_status["status"] != "matches_available":
            current_app.logger.warning(f"Attempted to get matches outside of matches_available phase. Current phase: {cycle_status['status']}")
            return []
        
        # Get the active cycle
        active_cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
        if not active_cycle:
            current_app.logger.warning("No active cycle found when fetching matches")
            return []
        
        # Get user matches from the active cycle only
        matches_query = Match.query.filter(
            ((Match.user1_email == email) | (Match.user2_email == email)) &
            (Match.cycle_id == active_cycle.id)  # Only get matches from current cycle
        ).order_by(Match.score.desc()).limit(3).all()
        
        # Get user's own data for comparison
        user_data = User.query.filter_by(email=email).first()
        if not user_data:
            current_app.logger.error(f"Could not find user data for {email}")
            return []
            
        # Convert user data to a dictionary for easier comparison
        user_filters = {
            'name': user_data.name,
            'gender': user_data.gender,
            'academic_year': user_data.academic_year,
            'preferred_years': user_data.preferred_years,
            'religion': user_data.religion,
            'preferred_religions': user_data.preferred_religions,
            'political_view': user_data.political_view,
            'preferred_political_views': user_data.preferred_political_views,
            'sexual_orientation': user_data.sexual_orientation
        }
        
        matches = []
        for match in matches_query:
            # Since we only query matches where user1_email == email, other_email is always user2_email
            other_email = match.user2_email if match.user1_email == email else match.user1_email
            
            # Get the other user's data for filter comparison
            other_user = User.query.filter_by(email=other_email).first()
            if not other_user:
                current_app.logger.error(f"Could not find data for match user {other_email}")
                continue
                
            # Log detailed filter data for debugging
            current_app.logger.info(f"User {email} filter data: " + 
                                f"Academic Year: {user_data.academic_year}, " +
                                f"Religion: {user_data.religion}, " +
                                f"Political View: {user_data.political_view}, " +
                                f"Preferred Religions: {user_data.preferred_religions}, " +
                                f"Preferred Political Views: {user_data.preferred_political_views}")
                                
            current_app.logger.info(f"Match {other_email} filter data: " + 
                                f"Academic Year: {other_user.academic_year}, " +
                                f"Religion: {other_user.religion}, " +
                                f"Political View: {other_user.political_view}, " +
                                f"Preferred Religions: {other_user.preferred_religions}, " +
                                f"Preferred Political Views: {other_user.preferred_political_views}")
                
            # Find shared filters
            shared_tags = []
            
            # Academic year
            if user_data.academic_year and other_user.academic_year and user_data.academic_year == other_user.academic_year:
                shared_tags.append({
                    'type': 'academic_year',
                    'value': user_data.academic_year
                })
                current_app.logger.info(f"Found shared academic year: {user_data.academic_year}")
                
            # Religion
            if user_data.religion and other_user.religion and user_data.religion == other_user.religion:
                shared_tags.append({
                    'type': 'religion',
                    'value': user_data.religion
                })
                current_app.logger.info(f"Found shared religion: {user_data.religion}")
                
            # Political view
            if user_data.political_view and other_user.political_view and user_data.political_view == other_user.political_view:
                shared_tags.append({
                    'type': 'political_view',
                    'value': user_data.political_view
                })
                current_app.logger.info(f"Found shared political view: {user_data.political_view}")
                
            # Check if user's religion is in match's preferred religions or vice versa
            if user_data.religion and other_user.preferred_religions and user_data.religion in other_user.preferred_religions:
                shared_tags.append({
                    'type': 'religion_preference',
                    'value': f"Prefers {user_data.religion}"
                })
                current_app.logger.info(f"Match prefers user's religion: {user_data.religion}")
                
            if other_user.religion and user_data.preferred_religions and other_user.religion in user_data.preferred_religions:
                shared_tags.append({
                    'type': 'religion_preference',
                    'value': f"You prefer {other_user.religion}"
                })
                current_app.logger.info(f"User prefers match's religion: {other_user.religion}")
                
            # Check if user's political view is in match's preferred views or vice versa
            if user_data.political_view and other_user.preferred_political_views and user_data.political_view in other_user.preferred_political_views:
                shared_tags.append({
                    'type': 'political_preference',
                    'value': f"Prefers {user_data.political_view}"
                })
                current_app.logger.info(f"Match prefers user's political view: {user_data.political_view}")
                
            if other_user.political_view and user_data.preferred_political_views and other_user.political_view in user_data.preferred_political_views:
                shared_tags.append({
                    'type': 'political_preference',
                    'value': f"You prefer {other_user.political_view}"
                })
                current_app.logger.info(f"User prefers match's political view: {other_user.political_view}")
            
            current_app.logger.info(f"Match between {email} and {other_email} has {len(shared_tags)} shared tags: {shared_tags}")
            
            matches.append({
                'match_id': match.id,
                'email': other_email,
                'name': other_user.name,
                'instagram_handle': other_user.instagram_handle,
                'score': match.score,
                'date_created': match.date_created.strftime('%Y-%m-%d %H:%M:%S') if match.date_created else None,
                'description': match.description,
                'shared_tags': shared_tags
            })
        
        return matches
    
    except Exception as e:
        current_app.logger.error(f"Error getting matches: {str(e)}")
        return []

@matches_bp.route('/get/<user_id>', methods=['GET'])
def get_matches_by_id(user_id):
    """Get matches for a specific user by user ID."""
    try:
        # Get the user's email based on user_id
        user = User.query.filter_by(id=user_id).first()
        
        if not user:
            return jsonify({"message": "User not found"}), 404
            
        return get_user_matches(user.email)
        
    except Exception as e:
        return jsonify({"message": f"Error getting matches: {str(e)}"}), 500

@matches_bp.route('/get_by_email', methods=['GET'])
def get_matches_by_email():
    """Get matches for a specific user by email."""
    email = request.args.get('email')
    if not email:
        return jsonify({"message": "Email parameter is required"}), 400
        
    return get_user_matches(email)

def get_user_matches(email):
    """Helper function to get matches for a user."""
    try:
        # Check the cycle status
        cycle_status = check_cycle_status()
        current_app.logger.info(f"Current cycle status: {cycle_status['status']}")
        current_app.logger.info(f"Checking matches for user: {email}")
        
        # Only show matches in the matches_available phase
        if cycle_status["status"] == "matches_available":
            current_app.logger.info("In matches_available phase, showing matches")
            
            # Get the user's matches even if there are none (will return empty list)
            matches = get_user_matches_internal(email)
            current_app.logger.info(f"Found {len(matches)} matches for user {email}")
            
            if matches:
                return jsonify({"matches": matches}), 200
            else:
                # No matches for this user specifically
                return jsonify({
                    "message": "No matches found for your profile. Please try again in the next matching cycle.",
                    "matches": []
                }), 200
        # If we're in the survey_open phase        
        elif cycle_status["status"] == "survey_open":
            message = "Matches will be available after the survey period ends and processing is complete."
            return jsonify({
                "message": message,
                "status": cycle_status["status"],
                "matches": []
            }), 200
        # If we're in the processing phase
        elif cycle_status["status"] == "processing":
            message = "Matches are being processed and will be available soon."
            return jsonify({
                "message": message,
                "status": cycle_status["status"],
                "matches": []
            }), 200
        # Fallback for any other statuses
        else:
            return jsonify({
                "message": "No matches available yet. Please check back later.",
                "matches": []
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Error in get_user_matches: {str(e)}")
        return jsonify({
            "message": f"An error occurred while retrieving matches: {str(e)}",
            "matches": []
        }), 500

def create_or_update_matching_attempt(cycle_id, success=False):
    """Create a new matching attempt record."""
    try:
        attempt = MatchingAttempt(
            cycle_id=cycle_id,
            attempt_time=get_central_time(),
            success=success,
            started_at=datetime.now(timezone.utc)
        )
        db.session.add(attempt)
        db.session.commit()
        current_app.logger.info(f"Created matching attempt for cycle #{cycle_id}")
        return attempt
    except Exception as e:
        current_app.logger.error(f"Error creating matching attempt: {str(e)}")
        db.session.rollback()
        return None
