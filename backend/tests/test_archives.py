from unittest.mock import Mock, patch

from app.archives.wayback import Way
from app.archives.archive_today import Arc

def test_archive_today_requires_manual_action():
    result = Arc().submit("https://example.com/")

    assert result.ok is False
    assert result.err == "manual_required"
    assert result.url.startswith(
        "https://archive.today/?run=1&url="
    )

def test_wayback_public_success(monkeypatch):
    monkeypatch.setattr(
        "app.archives.wayback.cfg.ia_key",
        "",
    )
    monkeypatch.setattr(
        "app.archives.wayback.cfg.ia_secret",
        "",
    )

    response = Mock()
    response.status_code = 302
    response.headers = {
        "location": (
            "https://web.archive.org/web/20260101/"
            "https://example.com/"
        )
    }

    with patch(
        "app.archives.wayback.httpx.get",
        return_value=response,
    ):
        result = Way().submit("https://example.com/")

    assert result.ok is True
    assert result.url.startswith(
        "https://web.archive.org/web/"
    )

def test_wayback_public_timeout(monkeypatch):
    monkeypatch.setattr(
        "app.archives.wayback.cfg.ia_key",
        "",
    )
    monkeypatch.setattr(
        "app.archives.wayback.cfg.ia_secret",
        "",
    )

    import httpx

    with patch(
        "app.archives.wayback.httpx.get",
        side_effect=httpx.TimeoutException("timed out"),
    ):
        result = Way().submit("https://example.com/")

    assert result.ok is False
    assert result.err.startswith("timeout:")

def test_wayback_auth_failure(monkeypatch):
    monkeypatch.setattr(
        "app.archives.wayback.cfg.ia_key",
        "test-key",
    )
    monkeypatch.setattr(
        "app.archives.wayback.cfg.ia_secret",
        "test-secret",
    )

    response = Mock()
    response.status_code = 401
    response.text = "unauthorized"

    with patch(
        "app.archives.wayback.httpx.post",
        return_value=response,
    ):
        result = Way().submit("https://example.com/")

    assert result.ok is False
    assert result.err == (
        "auth_required: Wayback credentials rejected"
    )

def test_wayback_authenticated_success(monkeypatch):
    monkeypatch.setattr(
        "app.archives.wayback.cfg.ia_key",
        "test-key",
    )
    monkeypatch.setattr(
        "app.archives.wayback.cfg.ia_secret",
        "test-secret",
    )

    submit_response = Mock()
    submit_response.status_code = 200
    submit_response.json.return_value = {
        "job_id": "abc123",
    }

    status_response = Mock()
    status_response.status_code = 200
    status_response.json.return_value = {
        "status": "success",
        "timestamp": "20260101123456",
        "original_url": "https://example.com/",
    }

    with patch(
        "app.archives.wayback.httpx.post",
        return_value=submit_response,
    ) as post, patch(
        "app.archives.wayback.httpx.get",
        return_value=status_response,
    ), patch(
        "app.archives.wayback.time.sleep",
    ):
        result = Way().submit("https://example.com/")

    assert result.ok is True
    assert result.aid == "abc123"
    assert result.url == (
        "https://web.archive.org/web/"
        "20260101123456/https://example.com/"
    )

    post.assert_called_once()
def test_wayback_authenticated_submission_error(monkeypatch):
    monkeypatch.setattr(
        "app.archives.wayback.cfg.ia_key",
        "test-key",
    )
    monkeypatch.setattr(
        "app.archives.wayback.cfg.ia_secret",
        "test-secret",
    )

    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "status": "error",
        "status_ext": "error:too-many-daily-captures",
        "message": (
            "This URL has been already captured 5 times today."
        ),
    }

    with patch(
        "app.archives.wayback.httpx.post",
        return_value=response,
    ):
        result = Way().submit("https://example.com/")

    assert result.ok is False
    assert result.err == (
        "This URL has been already captured 5 times today."
    )

def test_wayback_authenticated_capture_error(monkeypatch):
    monkeypatch.setattr(
        "app.archives.wayback.cfg.ia_key",
        "test-key",
    )
    monkeypatch.setattr(
        "app.archives.wayback.cfg.ia_secret",
        "test-secret",
    )

    submit_response = Mock()
    submit_response.status_code = 200
    submit_response.json.return_value = {
        "job_id": "abc123",
    }

    status_response = Mock()
    status_response.status_code = 200
    status_response.json.return_value = {
        "status": "error",
        "message": "capture failed",
    }

    with patch(
        "app.archives.wayback.httpx.post",
        return_value=submit_response,
    ), patch(
        "app.archives.wayback.httpx.get",
        return_value=status_response,
    ):
        result = Way().submit("https://example.com/")

    assert result.ok is False
    assert result.aid == "abc123"
    assert result.err == "capture failed"
