import pytest
from PySide6.QtCore import QUrl
from PySide6.QtNetwork import QNetworkAccessManager

from sshive.ui.icon_manager import IconManager, get_icon_manager


def test_icon_manager_instance(qtbot):
    """Test singleton instance access."""
    manager1 = IconManager.instance()
    manager2 = IconManager.instance()
    assert manager1 is manager2
    assert isinstance(manager1, IconManager)


def test_icon_manager_singleton_function(qtbot):
    """Test global get_icon_manager function."""
    manager1 = get_icon_manager()
    manager2 = get_icon_manager()
    assert manager1 is manager2


def test_manifest_url_curent(qtbot):
    """Ensure manifest URL is correct."""
    manager = IconManager.instance()
    assert manager.MANIFEST_URL == "https://raw.githubusercontent.com/selfhst/icons/main/index.json"


def test_parse_manifest_list(qtbot):
    """Test parsing of flat list manifest."""
    manager = IconManager()
    data = ["icon1", "icon2", "icon-3"]
    manager._parse_manifest(data)

    assert "icon1" in manager.valid_icons
    assert "icon2" in manager.valid_icons
    assert "icon-3" in manager.valid_icons
    assert "icon4" not in manager.valid_icons


def test_get_icon_path(qtbot, tmp_path):
    """Test get_icon_path with mocked cache."""
    manager = IconManager()
    # Mock cache dir
    manager.cache_dir = tmp_path

    # Create a dummy icon file
    icon_name = "test-icon"
    icon_file = tmp_path / f"{icon_name}.webp"
    icon_file.touch()

    path = manager.get_icon_path(icon_name)
    assert path == str(icon_file)

    # Test non-existent
    assert manager.get_icon_path("non-existent") is None
