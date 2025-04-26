from typing import Dict, Literal
from dataclasses import dataclass

@dataclass
class ColorPalette:
    background: str
    foreground: str
    accent: str
    error: str
    warning: str
    success: str
    disabled: str
    border: str
    hover: str
    selection: str

class AppStyle:
    """Manages application-wide styling with light and dark mode support."""
    
    # Color palettes for different themes
    _DARK_PALETTE = ColorPalette(
        background="#1e1e1e",
        foreground="#ffffff",
        accent="#4a9eff",
        error="#ff6b6b",
        warning="#ffd166",
        success="#06d6a0",
        disabled="#666666",
        border="#333333",
        hover="#2a2a2a",
        selection="#3a3a3a"
    )
    
    _LIGHT_PALETTE = ColorPalette(
        background="#ffffff",
        foreground="#000000",
        accent="#0066cc",
        error="#ff0000",
        warning="#ffa500",
        success="#00aa00",
        disabled="#999999",
        border="#cccccc",
        hover="#f0f0f0",
        selection="#e0e0e0"
    )
    
    def __init__(self, theme: Literal["dark", "light"] = "dark"):
        self._theme = theme
        self._palette = self._DARK_PALETTE if theme == "dark" else self._LIGHT_PALETTE
        
    @property
    def theme(self) -> str:
        return self._theme
        
    @theme.setter
    def theme(self, value: Literal["dark", "light"]):
        self._theme = value
        self._palette = self._DARK_PALETTE if value == "dark" else self._LIGHT_PALETTE
        
    def get_status_style(self, is_error: bool = False, is_disabled: bool = False) -> str:
        """Get the style for status labels."""
        color = self._palette.error if is_error else self._palette.disabled if is_disabled else self._palette.success
        return f"""
            color: {color};
            background-color: {self._palette.background};
            padding: 5px;
            border-radius: 3px;
            margin: 5px;
            border: 1px solid {self._palette.border};
        """
        
    def get_button_style(self) -> str:
        """Get the style for buttons."""
        return f"""
            QPushButton {{
                background-color: {self._palette.background};
                color: {self._palette.foreground};
                border: 1px solid {self._palette.border};
                border-radius: 3px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: {self._palette.hover};
            }}
            QPushButton:pressed {{
                background-color: {self._palette.selection};
            }}
            QPushButton:disabled {{
                color: {self._palette.disabled};
                background-color: {self._palette.background};
            }}
        """
        
    def get_input_style(self) -> str:
        """Get the style for input fields."""
        return f"""
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {self._palette.background};
                color: {self._palette.foreground};
                border: 1px solid {self._palette.border};
                border-radius: 3px;
                padding: 5px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 1px solid {self._palette.accent};
            }}
            QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
                color: {self._palette.disabled};
                background-color: {self._palette.background};
            }}
        """
        
    def get_tree_style(self) -> str:
        """Get the style for tree widgets."""
        return f"""
            QTreeWidget {{
                background-color: {self._palette.background};
                color: {self._palette.foreground};
                border: 1px solid {self._palette.border};
                border-radius: 3px;
            }}
            QTreeWidget::item {{
                padding: 5px;
            }}
            QTreeWidget::item:selected {{
                background-color: {self._palette.selection};
            }}
            QTreeWidget::item:hover {{
                background-color: {self._palette.hover};
            }}
        """
        
    def get_tab_style(self) -> str:
        """Get the style for tab widgets."""
        return f"""
            QTabWidget::pane {{
                border: 1px solid {self._palette.border};
                border-radius: 3px;
                background-color: {self._palette.background};
            }}
            QTabBar::tab {{
                background-color: {self._palette.background};
                color: {self._palette.foreground};
                border: 1px solid {self._palette.border};
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                padding: 5px 10px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {self._palette.selection};
            }}
            QTabBar::tab:hover {{
                background-color: {self._palette.hover};
            }}
        """
        
    def get_dialog_style(self) -> str:
        """Get the style for dialogs."""
        return f"""
            QDialog {{
                background-color: {self._palette.background};
                color: {self._palette.foreground};
            }}
            QDialogButtonBox QPushButton {{
                min-width: 80px;
            }}
        """
        
    def get_application_style(self) -> str:
        """Get the base application style."""
        return f"""
            QMainWindow, QWidget {{
                background-color: {self._palette.background};
                color: {self._palette.foreground};
            }}
            QMenuBar {{
                background-color: {self._palette.background};
                color: {self._palette.foreground};
                border-bottom: 1px solid {self._palette.border};
            }}
            QMenuBar::item:selected {{
                background-color: {self._palette.hover};
            }}
            QMenu {{
                background-color: {self._palette.background};
                color: {self._palette.foreground};
                border: 1px solid {self._palette.border};
            }}
            QMenu::item:selected {{
                background-color: {self._palette.selection};
            }}
            QScrollBar:vertical {{
                background-color: {self._palette.background};
                width: 12px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self._palette.border};
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """ 