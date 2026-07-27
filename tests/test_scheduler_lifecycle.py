"""Scheduler startup/shutdown lifecycle and job-safety configuration."""

import app.scheduler as scheduler_module
from app.core.config import settings


def test_job_has_duplicate_prevention_safety_options():
    scheduler = scheduler_module.create_scheduler()
    job = scheduler.get_job("send_daily_reminders")

    assert job is not None
    # A downtime window must never produce a burst of catch-up runs.
    assert job.max_instances == 1
    assert job.coalesce is True
    assert job.misfire_grace_time == settings.SCHEDULER_MISFIRE_GRACE_TIME


def test_start_scheduler_skipped_under_testing(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "testing")

    assert scheduler_module.start_scheduler() is None


def test_start_scheduler_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "SCHEDULER_ENABLED", False)

    assert scheduler_module.start_scheduler() is None


def test_start_and_shutdown_scheduler_once(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "SCHEDULER_ENABLED", True)

    scheduler = scheduler_module.start_scheduler()

    try:
        assert scheduler is not None
        assert scheduler.running is True
    finally:
        scheduler_module.shutdown_scheduler(scheduler)

    assert scheduler.running is False


def test_shutdown_is_safe_on_none():
    # Never raises even if the scheduler never started.
    scheduler_module.shutdown_scheduler(None)
