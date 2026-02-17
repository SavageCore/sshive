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
        palette = QApplication.palette()
        bg_color = palette.color(QPalette.ColorRole.Window)

        # Calculate luminance - if background is dark, we're in dark mode
        luminance = (
            0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()
        ) / 255

        return luminance < 0.5

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
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, dark_fg)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, dark_fg)
        dark_palette.setColor(QPalette.ColorRole.Text, dark_fg)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, dark_fg)
        dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        dark_palette.setColor(QPalette.ColorRole.Link, dark_highlight)
        dark_palette.setColor(QPalette.ColorRole.Highlight, dark_highlight)
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))

        # Disabled colors
        dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, dark_disabled)
        dark_palette.setColor(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, dark_disabled
        )

        app.setPalette(dark_palette)

        # Additional stylesheet tweaks
        app.setStyleSheet("""
            QTreeView::item:selected {
                background-color: #2a82da;
                color: white;
            }
            QTreeView::item:hover {
                background-color: #404040;
            }
            QPushButton {
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)

    @staticmethod
    def apply_light_theme(app: QApplication) -> None:
        """Apply light theme colors (uses system default).

        Args:
            app: QApplication instance
        """
        # Reset to default palette
        app.setPalette(app.style().standardPalette())

        # Minimal styling for consistency
        app.setStyleSheet("""
            QTreeView::item:hover {
                background-color: #e0e0e0;
            }
            QPushButton {
                padding: 5px 15px;
                border-radius: 3px;
            }
        """)
