"""Constants for cycle management and other system-wide settings."""

# Cycle durations
PROD_SURVEY_DAYS = 30
PROD_PROCESS_DAYS = 3
PROD_VIEW_DAYS = 3

TEST_CYCLE_MINUTES = 5

# Matching attempt settings
MAX_ATTEMPT_AGE_MINUTES = 3  # Consider attempt stale after 3 minutes
MAX_RETRY_COUNT = 2  # Maximum number of retries for failed match generation

# Recovery settings
RECOVERY_THROTTLE_SECONDS = 120  # Minimum seconds between recovery attempts

# Phase names (for consistency)
PHASE_SURVEY_OPEN = "survey_open"
PHASE_PROCESSING = "processing"
PHASE_MATCHES_AVAILABLE = "matches_available"
PHASE_EXPIRED = "expired"

# Feature flags
ENABLE_OPENAI = False  # Set to True to enable OpenAI descriptions 