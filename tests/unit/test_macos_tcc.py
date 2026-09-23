"""macOS TCC blocks reading the browser profile dir (EPERM), where
DevToolsActivePort lives. get_ws_url() must not crash on that: it falls back to a
dedicated automation Chrome, and fails with actionable guidance when it can't.
No real browser is launched."""
import pytest

from browser_harness import daemon


class _BlockedProfile:
    """A profile dir the OS refuses to read (macOS TCC / EPERM)."""

    def __truediv__(self, _name):
        return self

    def read_text(self, *args, **kwargs):
        raise PermissionError(1, "Operation not permitted")

    def __str__(self):
        return "/Library/Application Support/Google/Chrome"


@pytest.fixture
def blocked_profile(monkeypatch):
    monkeypatch.setattr(daemon, "PROFILES", [_BlockedProfile()])
    monkeypatch.delenv("BU_CDP_WS", raising=False)
    monkeypatch.delenv("BU_CDP_URL", raising=False)
    monkeypatch.setattr(daemon, "REMOTE_ID", None)

    def refused(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(daemon.urllib.request, "urlopen", refused)


def test_blocked_profile_falls_back_to_automation_chrome(blocked_profile, monkeypatch):
    monkeypatch.setattr(
        daemon, "launch_automation_chrome",
        lambda: "ws://127.0.0.1:9223/devtools/browser/auto",
    )
    assert daemon.get_ws_url() == "ws://127.0.0.1:9223/devtools/browser/auto"


def test_blocked_profile_without_browser_raises_actionable_error(blocked_profile, monkeypatch):
    monkeypatch.setattr(daemon, "launch_automation_chrome", lambda: None)
    with pytest.raises(RuntimeError, match="Full Disk Access"):
        daemon.get_ws_url()
