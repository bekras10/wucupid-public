from datetime import datetime
from sqlalchemy.sql import func
from .. import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=True)
    instagram_handle = db.Column(db.String(255), nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    academic_year = db.Column(db.String(20), nullable=True)
    preferred_years = db.Column(db.JSON, nullable=True)
    religion = db.Column(db.String(50), nullable=True)
    preferred_religions = db.Column(db.JSON, nullable=True)
    political_view = db.Column(db.String(50), nullable=True)
    preferred_political_views = db.Column(db.JSON, nullable=True)
    sexual_orientation = db.Column(db.String(20), nullable=True)
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_token = db.Column(db.String(255))
    verification_token_expires = db.Column(db.DateTime, nullable=True)
    password_reset_token = db.Column(db.String(255))
    password_reset_expires = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SurveyResponse(db.Model):
    __tablename__ = 'survey_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    looking_for = db.Column(db.String(10), nullable=False)
    responses = db.Column(db.JSON)
    contact_info = db.Column(db.JSON)
    is_submitted = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cycle_id = db.Column(db.Integer, db.ForeignKey('matching_cycles.id'), nullable=True)
    is_latest_progress = db.Column(db.Boolean, default=True)  # Flag to mark the latest progress for a user in a cycle
    
    # Define a unique constraint only for submitted surveys
    __table_args__ = (
        db.Index('idx_one_submission_per_cycle', 
                 'user_id', 'cycle_id', 'is_submitted',
                 unique=True,
                 postgresql_where=db.text("is_submitted = true")),
        db.Index('idx_latest_progress',
                 'user_id', 'cycle_id', 'is_latest_progress',
                 unique=True,
                 postgresql_where=db.text("is_latest_progress = true"))
    )

class Match(db.Model):
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    user1_email = db.Column(db.String(255), db.ForeignKey('users.email'))
    user2_email = db.Column(db.String(255), db.ForeignKey('users.email'))
    score = db.Column(db.Float)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    description = db.Column(db.Text, nullable=True)
    cycle_id = db.Column(db.Integer, db.ForeignKey('matching_cycles.id'), nullable=False, index=True)
    
    # Define a unique constraint on the user pair within a cycle
    __table_args__ = (
        db.UniqueConstraint('cycle_id', 'user1_email', 'user2_email', name='unique_match_pair_per_cycle'),
    )

class MatchingCycle(db.Model):
    __tablename__ = 'matching_cycles'
    
    id = db.Column(db.Integer, primary_key=True)
    cycle_number = db.Column(db.Integer, nullable=False)
    survey_start_date = db.Column(db.DateTime, nullable=False)
    survey_end_date = db.Column(db.DateTime, nullable=False)
    processing_end_date = db.Column(db.DateTime, nullable=False)
    matches_viewable_end = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    emails_sent = db.Column(db.Boolean, default=False)
    emails_sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_production_cycle = db.Column(db.Boolean, default=False)

class MatchingAttempt(db.Model):
    """Model for tracking match generation attempts."""
    __tablename__ = 'matching_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    cycle_id = db.Column(db.Integer, db.ForeignKey('matching_cycles.id'), nullable=False)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    success = db.Column(db.Boolean, nullable=False, default=False)
    error_text = db.Column(db.Text, nullable=True)
    attempt_time = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=True)  # Legacy column


class MatchEmailSend(db.Model):
    __tablename__ = 'match_email_sends'
    
    id = db.Column(db.Integer, primary_key=True)
    cycle_id = db.Column(db.Integer, db.ForeignKey('matching_cycles.id', ondelete='CASCADE'), nullable=False, index=True)
    recipient_email = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending' | 'sent' | 'error'
    error_text = db.Column(db.Text, nullable=True)
    attempt_count = db.Column(db.Integer, nullable=False, default=0)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('cycle_id', 'recipient_email', name='uq_match_email_send_cycle_recipient'),
        db.Index('idx_match_email_sends_cycle_pending', 'cycle_id', postgresql_where=db.text('sent_at IS NULL')),
    )
    
    def __repr__(self):
        return f"<MatchEmailSend cycle_id={self.cycle_id} recipient={self.recipient_email} status={self.status}>"
