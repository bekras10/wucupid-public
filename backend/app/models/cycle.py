from datetime import datetime, timedelta
from .. import db
from ..models.models import MatchingCycle, SurveyResponse, Match, MatchingAttempt, User
from sqlalchemy import desc
import os
import sys
import importlib.util
import inspect
from datetime import datetime, timezone, timedelta
import pytz
from ..config.constants import (
    PROD_SURVEY_DAYS, PROD_PROCESS_DAYS, PROD_VIEW_DAYS,
    TEST_CYCLE_MINUTES, PHASE_SURVEY_OPEN, PHASE_PROCESSING,
    PHASE_MATCHES_AVAILABLE, PHASE_EXPIRED
)
from ..utils.datetime_helpers import format_cycle_times

def get_central_time():
    """Get current time in Central timezone"""
    central = pytz.timezone('America/Chicago')
    return datetime.now(central)

def initialize_cycle_table():
    """
    Ensure exactly one active cycle exists (idempotent across workers).
    Uses a global advisory lock + double-check pattern to avoid
    multiple workers trying to create simultaneously.
    """
    from flask import current_app
    from sqlalchemy import func
    from ..utils.locking import acquire_global_init_lock, release_global_init_lock
    import time
    
    current_app.logger.info("init_cycle_enter")

    # Fast path (no lock) - if already there, return immediately
    active_cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
    if active_cycle:
        # Check if cycle is truly expired
        now = get_central_time()
        if now < active_cycle.matches_viewable_end:
            current_app.logger.info(
                f"init_cycle_existing_active cycle_number={active_cycle.cycle_number} "
                f"id={active_cycle.id} view_end={active_cycle.matches_viewable_end.isoformat()}"
            )
            return active_cycle
        current_app.logger.info(
            f"init_cycle_existing_expired cycle_number={active_cycle.cycle_number} "
            f"id={active_cycle.id} view_end={active_cycle.matches_viewable_end.isoformat()}"
        )

    # Slow path: attempt to create under advisory lock
    got_lock = acquire_global_init_lock()
    if not got_lock:
        # Another worker is creating; wait a tiny bit & read again
        current_app.logger.info("init_cycle_waiting_for_lock")
        db.session.commit()  # end current transaction if any
        time.sleep(0.5)
        active_cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
        now = get_central_time()
        if active_cycle and now < active_cycle.matches_viewable_end:
            current_app.logger.info(
                f"init_cycle_existing_after_wait cycle_number={active_cycle.cycle_number} "
                f"id={active_cycle.id} view_end={active_cycle.matches_viewable_end.isoformat()}"
            )
            return active_cycle
        # If still none, loop a couple of times
        for i in range(4):
            time.sleep(0.5)
            active_cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
            now = get_central_time()
            if active_cycle and now < active_cycle.matches_viewable_end:
                current_app.logger.info(
                    f"init_cycle_existing_after_retry_{i} cycle_number={active_cycle.cycle_number} "
                    f"id={active_cycle.id} view_end={active_cycle.matches_viewable_end.isoformat()}"
                )
                return active_cycle
        raise RuntimeError("Cycle initialization lock contention: active cycle still missing")

    try:
        # Re-check inside lock (double-check pattern)
        active_cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
        now = get_central_time()
        if active_cycle and now < active_cycle.matches_viewable_end:
            current_app.logger.info(
                f"init_cycle_existing_in_lock cycle_number={active_cycle.cycle_number} "
                f"id={active_cycle.id} view_end={active_cycle.matches_viewable_end.isoformat()}"
            )
            return active_cycle

        # No active cycle or expired: create one
        now = get_central_time()
        cycle_number = (db.session.query(func.max(MatchingCycle.cycle_number)).scalar() or 0) + 1
        
        # If there's an active cycle, mark it inactive
        if active_cycle:
            active_cycle.is_active = False
            db.session.commit()
            current_app.logger.info(
                f"init_cycle_deactivated cycle_number={active_cycle.cycle_number} "
                f"id={active_cycle.id}"
            )
        
        launch_datetime_str = os.environ.get('FIRST_CYCLE_START')
        try:
            # Parse launch datetime (assumed to be in Central Time)
            launch_datetime = datetime.strptime(launch_datetime_str, '%Y-%m-%d %H:%M:%S')
            launch_datetime = pytz.timezone('America/Chicago').localize(launch_datetime)
            
            # Determine if we're in production mode
            is_production = now >= launch_datetime
            
            if is_production:
                # Production cycle using constants
                survey_end = now + timedelta(days=PROD_SURVEY_DAYS)
                processing_end = survey_end + timedelta(days=PROD_PROCESS_DAYS)
                matches_viewable_end = processing_end + timedelta(days=PROD_VIEW_DAYS)
            else:
                # Test cycle using constants
                survey_end = now + timedelta(minutes=TEST_CYCLE_MINUTES)
                processing_end = survey_end + timedelta(minutes=TEST_CYCLE_MINUTES)
                matches_viewable_end = processing_end + timedelta(minutes=TEST_CYCLE_MINUTES)
            
        except (ValueError, TypeError) as e:
            current_app.logger.warning(f"init_cycle_launch_date_parse_error err={e}")
            # If launch date is invalid, default to test cycle
            survey_end = now + timedelta(minutes=TEST_CYCLE_MINUTES)
            processing_end = survey_end + timedelta(minutes=TEST_CYCLE_MINUTES)
            matches_viewable_end = processing_end + timedelta(minutes=TEST_CYCLE_MINUTES)
            is_production = False

        new_cycle = MatchingCycle(
            cycle_number=cycle_number,
            survey_start_date=now,
            survey_end_date=survey_end,
            processing_end_date=processing_end,
            matches_viewable_end=matches_viewable_end,
            is_active=True,
            is_production_cycle=is_production
        )
        
        try:
            db.session.add(new_cycle)
            db.session.commit()
            current_app.logger.info(
                f"init_cycle_created cycle_number={new_cycle.cycle_number} id={new_cycle.id} "
                f"survey_end={survey_end.isoformat()} proc_end={processing_end.isoformat()} "
                f"view_end={matches_viewable_end.isoformat()}"
            )
            return new_cycle
        except Exception as db_error:
            db.session.rollback()
            current_app.logger.error(f"init_cycle_db_error err={db_error}")
            # Another worker might have created the cycle, try to fetch it
            active_cycle = MatchingCycle.query.filter_by(is_active=True).first()
            if active_cycle:
                current_app.logger.info(
                    f"init_cycle_race_condition_recovered cycle_number={active_cycle.cycle_number} "
                    f"id={active_cycle.id}"
                )
                return active_cycle
            raise
    finally:
        release_global_init_lock()

def get_current_cycle():
    """Get the current active matching cycle"""
    cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
    
    if cycle:
        return {
            'id': cycle.id,
            'cycle_number': cycle.cycle_number,
            'survey_start_date': cycle.survey_start_date.strftime('%Y-%m-%d %H:%M:%S'),
            'survey_end_date': cycle.survey_end_date.strftime('%Y-%m-%d %H:%M:%S'),
            'processing_end_date': cycle.processing_end_date.strftime('%Y-%m-%d %H:%M:%S'),
            'is_active': cycle.is_active
        }
    else:
        return None

def create_next_cycle():
    """Create the next cycle after the current one ends"""
    from flask import current_app
    
    # Get current cycle first
    current_cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
    if not current_cycle:
        current_app.logger.info("create_next_cycle_no_active_cycle_found")
        return initialize_cycle_table()
    
    # Get cycle lock
    from ..utils.locking import acquire_cycle_lock, release_cycle_lock
    if not acquire_cycle_lock(current_cycle.id):
        current_app.logger.info("create_next_cycle_waiting_for_lock")
        # Another worker is creating; wait a bit & read
        db.session.commit()  # end current transaction if any
        import time
        time.sleep(0.5)
        active_cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
        if active_cycle:
            current_app.logger.info(
                f"create_next_cycle_existing_after_wait cycle_number={active_cycle.cycle_number} "
                f"id={active_cycle.id}"
            )
            return active_cycle
        # If still none, loop a couple of times
        for i in range(4):
            time.sleep(0.5)
            active_cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
            if active_cycle:
                current_app.logger.info(
                    f"create_next_cycle_existing_after_retry_{i} cycle_number={active_cycle.cycle_number} "
                    f"id={active_cycle.id}"
                )
                return active_cycle
        raise RuntimeError("Cycle creation lock contention: active cycle still missing")
    
    try:
        current_app.logger.info("create_next_cycle_got_lock")
        
        # Re-check current cycle inside lock
        current_cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
        if not current_cycle:
            current_app.logger.info("create_next_cycle_no_active_cycle_found_in_lock")
            return initialize_cycle_table()
        
        # Mark current cycle as inactive
        current_app.logger.info(
            f"create_next_cycle_found_active cycle_number={current_cycle.cycle_number} "
            f"id={current_cycle.id} is_active={current_cycle.is_active}"
        )
        current_cycle.is_active = False
        db.session.commit()
        current_app.logger.info(f"create_next_cycle_deactivated cycle_number={current_cycle.cycle_number}")
        
        # Get current time in UTC
        now = get_central_time()  # Changed to use Chicago time
        launch_datetime_str = os.environ.get('FIRST_CYCLE_START')
        
        try:
            # Parse launch datetime (assumed to be in Central Time)
            launch_datetime = datetime.strptime(launch_datetime_str, '%Y-%m-%d %H:%M:%S')
            launch_datetime = pytz.timezone('America/Chicago').localize(launch_datetime)
            
            current_app.logger.info(f"Launch datetime loaded and parsed successfully:")
            current_app.logger.info(f"  - Raw launch datetime string: {launch_datetime_str}")
            current_app.logger.info(f"  - Parsed Chicago time launch datetime: {launch_datetime}")
            current_app.logger.info(f"  - Current Chicago time: {now}")
            
            # Determine if we're in production mode (comparing in Chicago time)
            is_production = now >= launch_datetime
            
            current_app.logger.info(f"Production mode determination:")
            current_app.logger.info(f"  - Is production mode: {is_production}")
            current_app.logger.info(f"  - Logic: now ({now}) {'≥' if is_production else '<'} launch_datetime ({launch_datetime})")
            
            if is_production:
                # Production cycle using constants (all times in Chicago time)
                survey_end = now + timedelta(days=PROD_SURVEY_DAYS)
                processing_end = survey_end + timedelta(days=PROD_PROCESS_DAYS)
                matches_viewable_end = processing_end + timedelta(days=PROD_VIEW_DAYS)
                current_app.logger.info("Using PRODUCTION cycle periods:")
                current_app.logger.info(f"  - Survey period: {PROD_SURVEY_DAYS} days")
                current_app.logger.info(f"  - Processing period: {PROD_PROCESS_DAYS} days")
                current_app.logger.info(f"  - Viewing period: {PROD_VIEW_DAYS} days")
            else:
                # Test cycle using constants (all times in Chicago time)
                survey_end = now + timedelta(minutes=TEST_CYCLE_MINUTES)
                processing_end = survey_end + timedelta(minutes=TEST_CYCLE_MINUTES)
                matches_viewable_end = processing_end + timedelta(minutes=TEST_CYCLE_MINUTES)
                current_app.logger.info("Using TEST cycle periods:")
                current_app.logger.info(f"  - Each period length: {TEST_CYCLE_MINUTES} minutes")
                
        except (ValueError, TypeError) as e:
            current_app.logger.warning(f"create_next_cycle_launch_date_parse_error err={e}")
            # If launch date is invalid, default to test cycle (all times in Chicago time)
            survey_end = now + timedelta(minutes=TEST_CYCLE_MINUTES)
            processing_end = survey_end + timedelta(minutes=TEST_CYCLE_MINUTES)
            matches_viewable_end = processing_end + timedelta(minutes=TEST_CYCLE_MINUTES)
            is_production = False
        
        next_cycle = MatchingCycle(
            cycle_number=current_cycle.cycle_number + 1,
            survey_start_date=now,
            survey_end_date=survey_end,
            processing_end_date=processing_end,
            matches_viewable_end=matches_viewable_end,
            is_active=True,
            is_production_cycle=is_production
        )
        
        try:
            db.session.add(next_cycle)
            db.session.commit()
            current_app.logger.info(
                f"create_next_cycle_created cycle_number={next_cycle.cycle_number} id={next_cycle.id} "
                f"survey_end={survey_end.isoformat()} proc_end={processing_end.isoformat()} "
                f"view_end={matches_viewable_end.isoformat()}"
            )
            return next_cycle
        except Exception as db_error:
            db.session.rollback()
            current_app.logger.error(f"create_next_cycle_db_error err={db_error}")
            # Another worker might have created the cycle, try to fetch it
            active_cycle = MatchingCycle.query.filter_by(is_active=True).first()
            if active_cycle:
                current_app.logger.info(
                    f"create_next_cycle_race_condition_recovered cycle_number={active_cycle.cycle_number} "
                    f"id={active_cycle.id}"
                )
                return active_cycle
            raise
    finally:
        release_cycle_lock(current_cycle.id)
        current_app.logger.info("create_next_cycle_released_lock")

def compute_phase(now, cycle):
    """
    Pure function to compute the current phase of a cycle.
    Returns one of: survey_open, processing, matches_available, expired
    
    Args:
        now: timezone-aware datetime
        cycle: MatchingCycle instance with timezone-aware datetimes
    """
    # Ensure everything is UTC for comparison
    now_utc = now.astimezone(pytz.UTC)
    
    # Convert cycle times to UTC
    survey_end = cycle.survey_end_date.astimezone(pytz.UTC)
    processing_end = cycle.processing_end_date.astimezone(pytz.UTC)
    matches_viewable_end = cycle.matches_viewable_end.astimezone(pytz.UTC)
    
    # Log phase computation
    from flask import current_app
    current_app.logger.info(
        "cycle_tick_phase cycle_id=%s cycle_number=%s now_utc=%s survey_end_utc=%s proc_end_utc=%s view_end_utc=%s",
        cycle.id, cycle.cycle_number,
        now_utc.isoformat(),
        survey_end.isoformat(),
        processing_end.isoformat(),
        matches_viewable_end.isoformat()
    )
    
    # Compute phase
    if now_utc < survey_end:
        phase = PHASE_SURVEY_OPEN
    elif now_utc < processing_end:
        phase = PHASE_PROCESSING
    elif now_utc < matches_viewable_end:
        phase = PHASE_MATCHES_AVAILABLE
    else:
        phase = PHASE_EXPIRED
    
    current_app.logger.info(
        "cycle_tick_phase_result cycle_id=%s cycle_number=%s phase=%s",
        cycle.id, cycle.cycle_number, phase
    )
    
    return phase

def check_cycle_status():
    """
    Check current cycle status and take necessary actions
    Returns phase information and timing details
    """
    cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
    
    if not cycle:
        # Initialize if no cycle exists
        print("No active cycle found, initializing a new one")
        initialize_cycle_table()
        cycle = MatchingCycle.query.filter_by(is_active=True).order_by(desc(MatchingCycle.id)).first()
        if not cycle:
            print("Failed to create a new cycle")
            now = get_central_time()
            return format_cycle_times({
                "status": PHASE_SURVEY_OPEN,
                "cycle_number": 0,
                "time_remaining": 432000,
                "next_phase": PHASE_PROCESSING,
                "next_phase_date": now + timedelta(days=5),
                "survey_start_date": now,
                "survey_end_date": now + timedelta(days=5),
                "processing_end_date": now + timedelta(days=6)
            })
    
    now = get_central_time()
    current_phase = compute_phase(now, cycle)
    
    # Compute next phase and date
    if current_phase == PHASE_SURVEY_OPEN:
        next_phase = PHASE_PROCESSING
        next_date = cycle.survey_end_date
        time_remaining = max(0, (cycle.survey_end_date - now).total_seconds())
    elif current_phase == PHASE_PROCESSING:
        next_phase = PHASE_MATCHES_AVAILABLE
        next_date = cycle.processing_end_date
        time_remaining = max(0, (cycle.processing_end_date - now).total_seconds())
    elif current_phase == PHASE_MATCHES_AVAILABLE:
        next_phase = "new_cycle"
        next_date = cycle.matches_viewable_end
        time_remaining = max(0, (cycle.matches_viewable_end - now).total_seconds())
    else:  # expired
        next_phase = PHASE_SURVEY_OPEN
        next_date = now  # immediate
        time_remaining = 0
    
    return format_cycle_times({
        "status": current_phase,
        "cycle_number": cycle.cycle_number,
        "time_remaining": time_remaining,
        "next_phase": next_phase,
        "next_phase_date": next_date,
        "survey_start_date": cycle.survey_start_date,
        "survey_end_date": cycle.survey_end_date,
        "processing_end_date": cycle.processing_end_date
    }) 