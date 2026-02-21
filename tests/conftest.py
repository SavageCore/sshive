import pytest
from PySide6.QtCore import QSettings


@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Ensure singletons are cleaned up after every test to avoid segfaults."""
    yield
    try:
        from sshive.ui.icon_manager import reset_icon_manager

        reset_icon_manager()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch, tmp_path):
    """Redirect QSettings to a temporary file for every test."""
    # Create a wrapper that always points to our temp file
    settings_path = str(tmp_path / "test_settings.ini")

    # We patch the QSettings class in the modules that use it
    # to return a specifically configured instance.
    def get_mock_settings(*args, **kwargs):
        return QSettings(settings_path, QSettings.Format.IniFormat)

    # List of modules that import QSettings for window state
    monkeypatch.setattr("sshive.ui.main_window.QSettings", get_mock_settings)

    return settings_path


@pytest.fixture(autouse=True)
def block_icon_manager_network(monkeypatch):
    """Bypass IconManager network activity to keep tests fast and stable."""
    # Instead of a heavy mock, we just stub out the methods that hit the web
    from sshive.ui.icon_manager import IconManager

    monkeypatch.setattr(IconManager, "_load_manifest", lambda self: None)
    monkeypatch.setattr(IconManager, "fetch_icon", lambda self, name: None)

    return True
