"""Cycle orchestration service."""
from datetime import datetime
import os
import pytz
from sqlalchemy import desc, text
from flask import current_app
from .. import db
from ..models.models import MatchingCycle, Match as MatchModel, MatchingAttempt
from ..models.cycle import compute_phase, create_next_cycle, get_central_time
from ..utils.locking import (
    acquire_match_lock, release_match_lock,
    acquire_email_lock, release_email_lock,
    acquire_cycle_lock, release_cycle_lock
)
from ..utils.db_helpers import retry_on_db_error, ensure_fresh_connection
from ..config.constants import (
    PHASE_PROCESSING, PHASE_MATCHES_AVAILABLE, PHASE_EXPIRED,
    MAX_ATTEMPT_AGE_MINUTES, MAX_RETRY_COUNT
)

@retry_on_db_error(max_retries=3, delay=1)
def needs_recovery_generation(cycle_id):
    """Check if we need to attempt match generation recovery."""
    ensure_fresh_connection()
    
    # 1) No matches?
    if db.session.query(MatchModel.id).filter(MatchModel.cycle_id == cycle_id).first():
        return False
    
    # 2) No prior successful attempt?
    attempt = (db.session.query(MatchingAttempt)
               .filter(MatchingAttempt.cycle_id == cycle_id)
               .order_by(desc(MatchingAttempt.id))
               .first())
    
    # Allow retry if:
    # - No attempt yet
    # - Last attempt failed and we haven't hit retry limit
    # - Last attempt is stale (started but never finished)
    if attempt is None:
        return True
    
    if not attempt.success:
        retry_count = db.session.query(MatchingAttempt).filter(
            MatchingAttempt.cycle_id == cycle_id
        ).count()
        if retry_count < MAX_RETRY_COUNT:
            return True
    
    # Check for stale attempt
    if attempt.started_at and not attempt.finished_at:
        age_minutes = (datetime.now(pytz.UTC) - attempt.started_at).total_seconds() / 60
        if age_minutes > MAX_ATTEMPT_AGE_MINUTES:
            return True
    
    return False

@retry_on_db_error(max_retries=3, delay=1)
def run_cycle_tick():
    """
    Main orchestration function that runs every minute.
    Handles all cycle state transitions and side effects.
    
    NOTE: This orchestrator is safe with multiple containers
    because it uses Postgres advisory locks for exclusive sections.
    """
    ensure_fresh_connection()
    current_app.logger.info("cycle_tick_enter")
    
    # Get global cycle lock
    with db.engine.begin() as conn:
        # Try to get exclusive lock for cycle transitions; bail if busy
        got = conn.execute(text("SELECT pg_try_advisory_xact_lock(987654321)")).scalar()
        if not got:
            current_app.logger.info("cycle_tick_lock_busy")
            return
        
        # Get current cycle
        cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
        if not cycle:
            current_app.logger.warning("cycle_tick_no_active_cycle")
            return
        
        # Capture cycle_id early for logging
        cycle_id = cycle.id
        old_phase = None
        
        now = get_central_time()
        phase = compute_phase(now, cycle)
        
        # Get match count once to avoid multiple queries
        match_count = db.session.query(MatchModel).filter_by(cycle_id=cycle_id).count()
        
        # Log detailed cycle status
        current_app.logger.info(
            "cycle_tick_active cycle_id=%s number=%s phase=%s now_central=%s survey_end=%s proc_end=%s view_end=%s emails_sent=%s matches=%s",
            cycle_id, cycle.cycle_number, phase, now.isoformat(),
            cycle.survey_end_date.isoformat(),
            cycle.processing_end_date.isoformat(),
            cycle.matches_viewable_end.isoformat(),
            cycle.emails_sent,
            match_count
        )
        
        # 1. Handle expired phase - create next cycle
        if phase == PHASE_EXPIRED:
            current_app.logger.info(f"cycle_tick_expired cycle_id={cycle_id}")
            old_phase = phase
            
            # Re-check phase inside transaction
            cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
            if not cycle:
                current_app.logger.warning("cycle_tick_no_active_cycle_in_transaction")
                return
            
            now = get_central_time()
            phase = compute_phase(now, cycle)
            if phase == PHASE_EXPIRED:
                current_app.logger.info(f"cycle_tick_create_next cycle_id={cycle_id}")
                try:
                    next_cycle = create_next_cycle()
                    current_app.logger.info(
                        f"cycle_transition old={old_phase} new=survey_open "
                        f"old_cycle_id={cycle_id} old_number={cycle.cycle_number} "
                        f"new_cycle_id={next_cycle.id} new_number={next_cycle.cycle_number}"
                    )
                except Exception as e:
                    current_app.logger.error(f"cycle_tick_create_next_error cycle_id={cycle_id} err={e}")
            else:
                current_app.logger.info(f"cycle_tick_phase_changed_in_transaction cycle_id={cycle_id} new_phase={phase}")
            return
        
        # 2. Handle processing phase - generate matches
        if phase == PHASE_PROCESSING and needs_recovery_generation(cycle_id):
            old_phase = phase
            attempt = None
            try:
                from ..routes.matches import generate_matches_internal
                now_utc = datetime.now(pytz.UTC)
                attempt = MatchingAttempt(
                    cycle_id=cycle_id,
                    started_at=now_utc,
                    attempt_time=now_utc,  # Keep attempt_time in sync with started_at
                    success=False
                )
                db.session.add(attempt)
                db.session.flush()  # Get attempt.id without full commit
                
                current_app.logger.info(f"cycle_tick_match_attempt cycle_id={cycle_id} attempt_id={attempt.id}")
                
                result = generate_matches_internal(force=False)
                success = result.get('status_code', 500) == 200
                
                attempt.success = success
                attempt.finished_at = datetime.now(pytz.UTC)
                attempt.error_text = None if success else result.get('message')
                db.session.commit()
                
                current_app.logger.info(
                    f"cycle_tick_match_attempt_complete cycle_id={cycle_id} attempt_id={attempt.id} "
                    f"success={success}"
                )
                
                if success:
                    current_app.logger.info(
                        f"cycle_transition old={old_phase} new={phase} "
                        f"cycle_id={cycle_id} number={cycle.cycle_number} matches_generated=true"
                    )
            except Exception as e:
                db.session.rollback()
                if attempt:
                    try:
                        attempt.success = False
                        attempt.finished_at = datetime.now(pytz.UTC)
                        attempt.error_text = str(e)[:500]  # Truncate long errors
                        db.session.add(attempt)
                        db.session.commit()
                    except Exception as inner:
                        db.session.rollback()
                        current_app.logger.error(
                            f"cycle_tick_attempt_error_persist_failed cycle_id={cycle_id} "
                            f"attempt_id={attempt.id if attempt else None} err={inner}"
                        )
                current_app.logger.error(f"cycle_tick_match_attempt_failed cycle_id={cycle_id} err={e}")
        
        # 3. Handle matches_available phase - send emails once (no queue table)
        send_emails_info = None  # (cycle_number, [recipient_emails]) to send outside txn/locks
        if phase == PHASE_MATCHES_AVAILABLE:
            old_phase = phase
            # First check if we need recovery match generation
            if needs_recovery_generation(cycle_id):
                attempt = None
                try:
                    now_utc = datetime.now(pytz.UTC)
                    attempt = MatchingAttempt(
                        cycle_id=cycle_id,
                        started_at=now_utc,
                        attempt_time=now_utc,  # Keep attempt_time in sync with started_at
                        success=False
                    )
                    db.session.add(attempt)
                    db.session.flush()
                    
                    current_app.logger.info(f"cycle_tick_recovery_attempt cycle_id={cycle_id} attempt_id={attempt.id}")
                    
                    from ..routes.matches import generate_matches_internal
                    result = generate_matches_internal(force=True)  # Use force=True for recovery
                    
                    attempt.success = result.get('status_code', 500) == 200
                    attempt.finished_at = datetime.now(pytz.UTC)
                    attempt.error_text = None if attempt.success else result.get('message')
                    db.session.commit()
                    
                    current_app.logger.info(
                        f"cycle_tick_recovery_attempt_complete cycle_id={cycle_id} attempt_id={attempt.id} "
                        f"success={attempt.success}"
                    )
                    
                    if attempt.success:
                        current_app.logger.info(
                            f"cycle_transition old={old_phase} new={phase} "
                            f"cycle_id={cycle_id} number={cycle.cycle_number} matches_recovered=true"
                        )
                except Exception as e:
                    db.session.rollback()
                    if attempt:
                        try:
                            attempt.success = False
                            attempt.finished_at = datetime.now(pytz.UTC)
                            attempt.error_text = str(e)[:500]
                            db.session.add(attempt)
                            db.session.commit()
                        except Exception as inner:
                            db.session.rollback()
                            current_app.logger.error(
                                f"cycle_tick_recovery_error_persist_failed cycle_id={cycle_id} "
                                f"attempt_id={attempt.id if attempt else None} err={inner}"
                            )
                    current_app.logger.error(f"cycle_tick_recovery_attempt_failed cycle_id={cycle_id} err={e}")
            
            # Then send match-available emails once per cycle (guarded by MatchingCycle.emails_sent)
            matches_exist = match_count > 0
            if not cycle.emails_sent and matches_exist:
                if not acquire_email_lock(cycle_id):
                    current_app.logger.info(f"cycle_tick_email_lock_busy cycle_id={cycle_id}")
                    return
                try:
                    # Re-check inside lock
                    cycle = MatchingCycle.query.filter_by(id=cycle_id).first()
                    if cycle.emails_sent:
                        current_app.logger.info(f"cycle_tick_emails_already_sent cycle_id={cycle_id}")
                        return
                    # Emergency kill switch via env
                    kill_emails = os.environ.get('DISABLE_OUTBOUND_EMAILS', '').lower() in ('1','true','on','yes') or \
                                   os.environ.get('DISABLE_MATCH_EMAILS', '').lower() in ('1','true','on','yes')
                    if kill_emails:
                        current_app.logger.warning(f"cycle_tick_email_skipped_by_env cycle_id={cycle_id}")
                        cycle.emails_sent = True
                        cycle.emails_sent_at = datetime.now(pytz.UTC)
                        db.session.commit()
                        return
                    from ..models.models import User, SurveyResponse
                    # Compute intended recipients for current cycle
                    users_with_matches = db.session.query(User.email).join(
                        SurveyResponse, User.id == SurveyResponse.user_id
                    ).join(
                        MatchModel, (User.email == MatchModel.user1_email) | (User.email == MatchModel.user2_email)
                    ).filter(
                        User.is_email_verified == True,
                        SurveyResponse.is_submitted == True,
                        SurveyResponse.cycle_id == cycle_id,
                        MatchModel.cycle_id == cycle_id
                    ).distinct().all()
                    email_list = [user.email for user in users_with_matches]
                    current_app.logger.info(
                        f"matches_available_email_recipients cycle_id={cycle_id} intended={len(email_list)}"
                    )
                    if not email_list:
                        # This should be rare if match_count > 0. Avoid permanently skipping a cycle due to
                        # a query mismatch (e.g., timestamp window / cycle_id issues); retry on next tick.
                        current_app.logger.error(
                            f"matches_available_email_no_recipients cycle_id={cycle_id} "
                            f"match_count={match_count} emails_sent_left_false=true"
                        )
                        return

                    # Mark as done BEFORE sending to ensure at-most-once per cycle.
                    cycle.emails_sent = True
                    cycle.emails_sent_at = datetime.now(pytz.UTC)
                    db.session.commit()
                    current_app.logger.info(f"matches_available_email_claimed cycle_id={cycle_id} emails_sent_set=true")

                    # Defer actual sending until after transaction/locks
                    send_emails_info = (cycle.cycle_number, email_list)
                except Exception as e:
                    current_app.logger.error(f"cycle_tick_email_send_prep_error cycle_id={cycle_id} err={e}")
                finally:
                    release_email_lock(cycle_id)
    # After transaction finishes, perform sending outside long transaction / advisory locks
    if 'send_emails_info' in locals() and send_emails_info:
        _number, _emails = send_emails_info
        try:
            from ..email import send_matches_available_email
            success_count = 0
            failure_count = 0
            current_app.logger.info(
                f"matches_available_email_run_start cycle_number={_number} intended={len(_emails)}"
            )
            for email in _emails:
                try:
                    current_app.logger.info(f"attempting_matches_available_email to={email} cycle_number={_number}")
                    ok = send_matches_available_email(email, _number)
                    if ok:
                        success_count += 1
                        current_app.logger.info(f"successfully_sent_matches_available_email to={email} cycle_number={_number}")
                    else:
                        failure_count += 1
                        current_app.logger.warning(f"failed_to_send_matches_available_email to={email} cycle_number={_number}")
                except Exception as inner:
                    failure_count += 1
                    current_app.logger.error(
                        f"matches_available_email_exception to={email} cycle_number={_number} err={inner}"
                    )
            current_app.logger.info(
                f"matches_available_email_run_done cycle_number={_number} success={success_count} failed={failure_count}"
            )
        except Exception as e:
            current_app.logger.error(f"matches_available_email_run_error cycle_number={_number} err={e}")

    try:
        status = db.engine.pool.status()
    except Exception:
        status = "unknown"
    current_app.logger.info({"event": "cycle_tick_exit", "pool_status": status})