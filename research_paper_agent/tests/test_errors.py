# Error handling test assertions without pytest dependency
from research_paper_agent.errors import (
    RetryableError,
    NonRetryableError,
    retry_with_backoff,
    make_error_entry,
    make_log_entry,
)


def test_retry_success_after_failure():
    attempts = 0

    @retry_with_backoff(max_retries=2, base_delay=0.01, jitter=False)
    def flaky_func():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise RetryableError("Temporary glitch")
        return "success"

    result = flaky_func()
    assert result == "success"
    assert attempts == 2


def test_non_retryable_propagates_immediately():
    attempts = 0

    @retry_with_backoff(max_retries=3, base_delay=0.01)
    def fail_hard():
        nonlocal attempts
        attempts += 1
        raise NonRetryableError("Invalid API key")

    raised = False
    try:
        fail_hard()
    except NonRetryableError:
        raised = True
    assert raised is True
    assert attempts == 1


def test_make_error_and_log_entry():
    err = make_error_entry("source_validator", ValueError("Bad URL"), retryable=False, fallback_used="skip")
    assert err["node"] == "source_validator"
    assert err["retryable"] is False
    assert err["fallback_used"] == "skip"

    log = make_log_entry("research_planner", "SUCCESS", "queries=6")
    assert "[research_planner] SUCCESS queries=6" in log
