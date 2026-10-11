import pytest
from pydantic import ValidationError

from app.schemas.job import JobCreate


def _payload(**overrides):
    data = {
        "event_name": "Bootcamp",
        "issue_date": "2026-10-15",
        "recipients": [{"name": "Alex", "email": "alex@example.com"}],
    }
    data.update(overrides)
    return data


def test_valid_job_create():
    job = JobCreate(**_payload())
    assert len(job.recipients) == 1


def test_empty_recipients_rejected():
    with pytest.raises(ValidationError):
        JobCreate(**_payload(recipients=[]))


def test_invalid_email_rejected():
    with pytest.raises(ValidationError):
        JobCreate(**_payload(recipients=[{"name": "Alex", "email": "nope"}]))


def test_missing_event_name_rejected():
    data = _payload()
    del data["event_name"]
    with pytest.raises(ValidationError):
        JobCreate(**data)
