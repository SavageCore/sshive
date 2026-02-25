"""Theme management for dark/light mode."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class ThemeManager:
    """Manages application theme (dark/light mode)."""

    @staticmethod
    def is_system_dark_mode() -> bool:
        """Detect if system is using dark mode.

        Returns:
            True if dark mode is active
        """
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication

        # 1. Try Qt 6.5+ style hints (most reliable)
        try:
            hints = QGuiApplication.styleHints()
            if hasattr(Qt.ColorScheme, "Dark"):
                return hints.colorScheme() == Qt.ColorScheme.Dark
        except (AttributeError, ImportError):
            pass

        # 2. Fallback: Check the standard palette of the style (Fusion)
        # We don't use QApplication.palette() because it may have been overridden by us
        app = QApplication.instance()
        if app:
            palette = app.style().standardPalette()
            bg_color = palette.color(QPalette.ColorRole.Window)
            luminance = (
                0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()
            ) / 255
            return luminance < 0.5

        return False

    @staticmethod
    def apply_theme(app: QApplication) -> None:
        """Apply appropriate theme based on system settings.

        Args:
            app: QApplication instance
        """
        if ThemeManager.is_system_dark_mode():
            ThemeManager.apply_dark_theme(app)
        else:
            ThemeManager.apply_light_theme(app)

    @staticmethod
    def apply_dark_theme(app: QApplication) -> None:
        """Apply dark theme colors.

        Args:
            app: QApplication instance
        """
        dark_palette = QPalette()

        # Colors
        dark_bg = QColor(45, 45, 45)
        dark_fg = QColor(255, 255, 255)
        dark_highlight = QColor(42, 130, 218)
        dark_disabled = QColor(127, 127, 127)

        dark_palette.setColor(QPalette.ColorRole.Window, dark_bg)
        dark_palette.setColor(QPalette.ColorRole.WindowText, dark_fg)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        dark_palette.setColor(QPalette.ColorRole.Text, dark_fg)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, dark_fg)
        dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        dark_palette.setColor(QPalette.ColorRole.Link, dark_highlight)
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(80, 80, 80))  # subtle gray
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, dark_fg)  # white

        # Disabled colors
        dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, dark_disabled)
        dark_palette.setColor(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, dark_disabled
        )

        app.setPalette(dark_palette)

        # Additional stylesheet tweaks
        app.setStyleSheet("""
            QTreeView {
                selection-background-color: #505050;
                selection-color: white;
                show-decoration-selected: 1;
                outline: none;
                border: none;
            }
            QHeaderView::section {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 4px 6px;
                border: 1px solid #505050;
                border-top: none;
                border-left: none;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QLineEdit {
                padding: 4px 8px;
                border: 1px solid #505050;
                border-radius: 4px;
                background-color: #3d3d3d;
                color: #ffffff;
                selection-background-color: #505050;
            }
            QLineEdit:focus {
                border-color: #4282da;
            }
            QToolButton {
            }
            QPushButton {
                padding: 5px 15px;
                border-radius: 4px;
                border: 1px solid #505050;
                background-color: #3d3d3d;
            }
            QPushButton:hover {
                background-color: #505050;
                border-color: #606060;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
            QPushButton:disabled {
                border-color: #353535;
                background-color: #353535;
                color: #7f7f7f;
            }
        """)

    @staticmethod
    def apply_light_theme(app: QApplication) -> None:
        """Apply light theme colors using QPalette to preserve native styling.

        Args:
            app: QApplication instance
        """
        app.setStyle("Fusion")

        # Build a full Light Palette so we don't rely on the system's standard palette (which may be dark)
        light_palette = QPalette()
        light_palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        light_palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        light_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        light_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        light_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        light_palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        light_palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        light_palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        light_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        light_palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))

        # Selection colors
        light_palette.setColor(QPalette.ColorRole.Highlight, QColor(204, 232, 255))
        light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))

        # Disabled colors
        light_disabled = QColor(127, 127, 127)
        light_palette.setColor(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, light_disabled
        )
        light_palette.setColor(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, light_disabled
        )
        light_palette.setColor(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, light_disabled
        )

        app.setPalette(light_palette)

        # Minimal styling that doesn't break Fusion's native QTreeView drawing.
        app.setStyleSheet("""
            QTreeView {
                show-decoration-selected: 1;
                outline: none;
                border: none;
            }
            QPushButton {
                padding: 5px 15px;
                border-radius: 4px;
                border: 1px solid rgba(0, 0, 0, 0.2);
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
                border-color: rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.15);
            }
            QPushButton:disabled {
                border-color: rgba(0, 0, 0, 0.1);
                background-color: rgba(0, 0, 0, 0.05);
            }
            QLineEdit {
                padding: 4px 8px;
                border: 1px solid rgba(0, 0, 0, 0.3);
                border-radius: 4px;
            }
            QLineEdit:focus {
                border-color: #0078D7;
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                color: #000000;
                padding: 4px 6px;
                border: 1px solid #cccccc;
                border-top: none;
                border-left: none;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QToolButton {
                border: none;
            }
        """)
