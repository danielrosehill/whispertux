#!/usr/bin/env python3
"""
WhisperTux Fork - Voice dictation application for Linux
PySide6 GUI with modern styling and KDE Plasma integration
"""

import sys
import threading
import time
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame, QComboBox, QDialog,
    QScrollArea, QLineEdit, QCheckBox, QSpinBox, QMessageBox,
    QFileDialog, QListWidget, QListWidgetItem, QButtonGroup,
    QRadioButton, QGroupBox, QSizePolicy, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QSize
from PySide6.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QPainter, QAction
)

# Import custom modules
from src.audio_capture import AudioCapture
from src.whisper_manager import WhisperManager
from src.text_injector import TextInjector
from src.config_manager import ConfigManager
from src.global_shortcuts import GlobalShortcuts, get_available_keyboards


# Color scheme
COLORS = {
    'background': '#1e1e2e',
    'surface': '#2a2a3c',
    'surface_light': '#363649',
    'primary': '#89b4fa',
    'primary_dark': '#7aa2f7',
    'success': '#a6e3a1',
    'warning': '#f9e2af',
    'error': '#f38ba8',
    'text': '#cdd6f4',
    'text_dim': '#9399b2',
    'border': '#45475a',
}


def get_stylesheet():
    """Return the application stylesheet"""
    return f"""
        QMainWindow, QDialog {{
            background-color: {COLORS['background']};
        }}

        QWidget {{
            color: {COLORS['text']};
            font-family: 'Noto Sans', 'Segoe UI', sans-serif;
        }}

        QFrame#card {{
            background-color: {COLORS['surface']};
            border-radius: 12px;
            border: 1px solid {COLORS['border']};
        }}

        QLabel {{
            color: {COLORS['text']};
        }}

        QLabel#title {{
            font-size: 24px;
            font-weight: bold;
            color: {COLORS['primary']};
        }}

        QLabel#subtitle {{
            font-size: 13px;
            color: {COLORS['text_dim']};
        }}

        QLabel#section_title {{
            font-size: 15px;
            font-weight: bold;
            color: {COLORS['text']};
        }}

        QLabel#status_ready {{
            font-size: 15px;
            font-weight: bold;
            color: {COLORS['success']};
        }}

        QLabel#status_recording {{
            font-size: 15px;
            font-weight: bold;
            color: {COLORS['error']};
        }}

        QLabel#status_processing {{
            font-size: 15px;
            font-weight: bold;
            color: {COLORS['warning']};
        }}

        QLabel#info_label {{
            font-size: 13px;
            color: {COLORS['text_dim']};
        }}

        QLabel#info_value {{
            font-size: 13px;
            font-weight: bold;
            color: {COLORS['primary']};
        }}

        QPushButton {{
            background-color: {COLORS['surface_light']};
            color: {COLORS['text']};
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: 500;
        }}

        QPushButton:hover {{
            background-color: {COLORS['border']};
        }}

        QPushButton:pressed {{
            background-color: {COLORS['surface']};
        }}

        QPushButton:disabled {{
            background-color: {COLORS['surface']};
            color: {COLORS['text_dim']};
        }}

        QPushButton#primary {{
            background-color: {COLORS['success']};
            color: {COLORS['background']};
            font-weight: bold;
        }}

        QPushButton#primary:hover {{
            background-color: #8bd49a;
        }}

        QPushButton#danger {{
            background-color: {COLORS['error']};
            color: {COLORS['background']};
        }}

        QPushButton#danger:hover {{
            background-color: #e57a96;
        }}

        QPushButton#recording {{
            background-color: {COLORS['error']};
            color: {COLORS['background']};
            font-weight: bold;
        }}

        QTextEdit {{
            background-color: {COLORS['surface']};
            color: {COLORS['text']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            padding: 12px;
            font-size: 14px;
            font-family: 'Noto Sans Mono', 'Consolas', monospace;
        }}

        QComboBox {{
            background-color: {COLORS['surface']};
            color: {COLORS['text']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
            min-width: 200px;
        }}

        QComboBox:hover {{
            border-color: {COLORS['primary']};
        }}

        QComboBox::drop-down {{
            border: none;
            padding-right: 10px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {COLORS['surface']};
            color: {COLORS['text']};
            selection-background-color: {COLORS['primary']};
            selection-color: {COLORS['background']};
            border: 1px solid {COLORS['border']};
        }}

        QLineEdit {{
            background-color: {COLORS['surface']};
            color: {COLORS['text']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
        }}

        QLineEdit:focus {{
            border-color: {COLORS['primary']};
        }}

        QSpinBox {{
            background-color: {COLORS['surface']};
            color: {COLORS['text']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 13px;
        }}

        QSpinBox::up-button, QSpinBox::down-button {{
            background-color: {COLORS['surface_light']};
            border: none;
            width: 20px;
        }}

        QSpinBox::up-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-bottom: 5px solid {COLORS['text']};
            width: 0;
            height: 0;
        }}

        QSpinBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {COLORS['text']};
            width: 0;
            height: 0;
        }}

        QDialog QLabel {{
            color: {COLORS['text']};
            font-size: 13px;
        }}

        QCheckBox {{
            font-size: 13px;
            spacing: 8px;
            color: {COLORS['text']};
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 2px solid {COLORS['border']};
            background-color: {COLORS['surface']};
        }}

        QCheckBox::indicator:checked {{
            background-color: {COLORS['primary']};
            border-color: {COLORS['primary']};
        }}

        QListWidget {{
            background-color: {COLORS['surface']};
            color: {COLORS['text']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            font-size: 13px;
        }}

        QListWidget::item {{
            padding: 6px;
        }}

        QListWidget::item:selected {{
            background-color: {COLORS['primary']};
            color: {COLORS['background']};
        }}

        QScrollArea {{
            border: none;
            background-color: transparent;
        }}

        QScrollBar:vertical {{
            background-color: {COLORS['surface']};
            width: 10px;
            border-radius: 5px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {COLORS['border']};
            border-radius: 5px;
            min-height: 30px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {COLORS['text_dim']};
        }}

        QGroupBox {{
            font-size: 14px;
            font-weight: bold;
            color: {COLORS['primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            margin-top: 16px;
            padding: 16px 12px 12px 12px;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            top: 4px;
            padding: 0 8px;
            background-color: {COLORS['background']};
            color: {COLORS['primary']};
        }}

        QRadioButton {{
            font-size: 13px;
            spacing: 8px;
        }}

        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: 2px solid {COLORS['border']};
            background-color: {COLORS['surface']};
        }}

        QRadioButton::indicator:checked {{
            background-color: {COLORS['primary']};
            border-color: {COLORS['primary']};
        }}
    """


class AudioLevelWidget(QWidget):
    """Simple audio level meter widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0.0
        self.is_recording = False
        self.setMinimumHeight(30)
        self.setMaximumHeight(30)

    def set_level(self, level: float):
        """Set the audio level (0.0 to 1.0)"""
        self.level = max(0.0, min(1.0, level))
        self.update()

    def set_recording(self, recording: bool):
        """Set recording state"""
        self.is_recording = recording
        if not recording:
            self.level = 0.0
        self.update()

    def paintEvent(self, event):
        """Paint the level meter"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        bg_color = QColor(COLORS['surface'])
        painter.fillRect(self.rect(), bg_color)

        # Border
        painter.setPen(QColor(COLORS['border']))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)

        # Level bar
        if self.is_recording and self.level > 0:
            bar_width = int((self.width() - 8) * self.level)
            bar_rect = self.rect().adjusted(4, 4, -4, -4)
            bar_rect.setWidth(bar_width)

            # Color based on level
            if self.level < 0.5:
                color = QColor(COLORS['success'])
            elif self.level < 0.8:
                color = QColor(COLORS['warning'])
            else:
                color = QColor(COLORS['error'])

            painter.fillRect(bar_rect, color)

        # Level markers
        painter.setPen(QColor(COLORS['border']))
        for pct in [0.25, 0.5, 0.75]:
            x = int(4 + (self.width() - 8) * pct)
            painter.drawLine(x, 4, x, self.height() - 4)


class SignalEmitter(QObject):
    """Helper class to emit signals from non-Qt threads"""
    transcription_ready = Signal(str)
    status_update = Signal(str)
    recording_state = Signal(bool)


class SettingsDialog(QDialog):
    """Settings dialog for WhisperTux"""

    def __init__(self, parent, config: ConfigManager, global_shortcuts: GlobalShortcuts,
                 whisper_manager: WhisperManager, update_callback):
        super().__init__(parent)
        self.config = config
        self.global_shortcuts = global_shortcuts
        self.whisper_manager = whisper_manager
        self.update_callback = update_callback

        self.setWindowTitle("WhisperTux Settings")
        self.setMinimumSize(550, 700)
        self.setModal(True)

        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        """Set up the settings UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)

        # Shortcuts section
        shortcuts_group = self._create_shortcuts_section()
        scroll_layout.addWidget(shortcuts_group)

        # Model section
        model_group = self._create_model_section()
        scroll_layout.addWidget(model_group)

        # Model directories section
        dirs_group = self._create_directories_section()
        scroll_layout.addWidget(dirs_group)

        # General settings section
        general_group = self._create_general_section()
        scroll_layout.addWidget(general_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setObjectName("danger")
        reset_btn.clicked.connect(self._reset_defaults)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_shortcuts_section(self):
        """Create shortcuts configuration section"""
        group = QGroupBox("Global Shortcuts")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Current shortcut display
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Current Shortcut:"))
        self.current_shortcut_label = QLabel(self.config.get_setting('primary_shortcut', 'F12'))
        self.current_shortcut_label.setObjectName("info_value")
        current_layout.addWidget(self.current_shortcut_label)
        current_layout.addStretch()
        layout.addLayout(current_layout)

        # New shortcut selection
        shortcut_layout = QHBoxLayout()
        shortcut_layout.addWidget(QLabel("New Shortcut:"))
        self.shortcut_combo = QComboBox()
        self.shortcut_combo.addItems(self._get_shortcut_options())
        shortcut_layout.addWidget(self.shortcut_combo)
        shortcut_layout.addStretch()
        layout.addLayout(shortcut_layout)

        return group

    def _create_model_section(self):
        """Create model configuration section"""
        group = QGroupBox("Whisper Model")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self._refresh_model_list()
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        layout.addLayout(model_layout)

        return group

    def _create_directories_section(self):
        """Create model directories section"""
        group = QGroupBox("Model Directories")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Directory list
        self.dirs_list = QListWidget()
        self.dirs_list.setMaximumHeight(100)
        layout.addWidget(self.dirs_list)

        # Add directory
        add_layout = QHBoxLayout()
        self.new_dir_entry = QLineEdit()
        self.new_dir_entry.setPlaceholderText("Enter directory path...")
        add_layout.addWidget(self.new_dir_entry)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_directory)
        add_layout.addWidget(browse_btn)
        layout.addLayout(add_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_directory)
        btn_layout.addWidget(add_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_directory)
        btn_layout.addWidget(remove_btn)

        btn_layout.addStretch()

        refresh_btn = QPushButton("Refresh Models")
        refresh_btn.clicked.connect(self._refresh_models)
        btn_layout.addWidget(refresh_btn)
        layout.addLayout(btn_layout)

        return group

    def _create_general_section(self):
        """Create general settings section"""
        group = QGroupBox("General Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Always on top
        self.always_on_top_cb = QCheckBox("Keep window always on top")
        layout.addWidget(self.always_on_top_cb)

        # Key delay
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Key Delay (ms):"))
        self.key_delay_spin = QSpinBox()
        self.key_delay_spin.setRange(1, 200)
        self.key_delay_spin.setValue(15)
        delay_layout.addWidget(self.key_delay_spin)
        delay_layout.addStretch()
        layout.addLayout(delay_layout)

        # Microphone
        mic_layout = QHBoxLayout()
        mic_layout.addWidget(QLabel("Microphone:"))
        self.mic_combo = QComboBox()
        self._load_microphones()
        mic_layout.addWidget(self.mic_combo)
        mic_layout.addStretch()
        layout.addLayout(mic_layout)

        # Keyboard device
        kb_layout = QHBoxLayout()
        kb_layout.addWidget(QLabel("Keyboard Device:"))
        self.kb_combo = QComboBox()
        self._load_keyboards()
        kb_layout.addWidget(self.kb_combo)
        kb_layout.addStretch()
        layout.addLayout(kb_layout)

        return group

    def _get_shortcut_options(self):
        """Get available shortcut options"""
        options = ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
                   'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 'F20']
        for prefix in ['Ctrl+', 'Alt+', 'Shift+', 'Super+']:
            for fkey in ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12']:
                options.append(f'{prefix}{fkey}')
        return options

    def _refresh_model_list(self):
        """Refresh the model dropdown"""
        self.model_combo.clear()
        models = self.whisper_manager.get_available_models() if self.whisper_manager else []
        if models:
            self.model_combo.addItems(models)
        else:
            self.model_combo.addItem("No models found")

    def _load_microphones(self):
        """Load available microphones"""
        self.mic_combo.clear()
        self.mic_combo.addItem("System Default", None)
        self.mic_device_map = {0: None}

        try:
            devices = AudioCapture.get_available_input_devices()
            for i, device in enumerate(devices, 1):
                self.mic_combo.addItem(device['display_name'], device['id'])
                self.mic_device_map[i] = device['id']
        except Exception as e:
            print(f"Error loading microphones: {e}")

    def _load_keyboards(self):
        """Load available keyboards"""
        self.kb_combo.clear()
        self.kb_combo.addItem("Auto-detect (All Keyboards)", "")
        self.kb_device_map = {0: ""}

        try:
            keyboards = get_available_keyboards()
            for i, kb in enumerate(keyboards, 1):
                self.kb_combo.addItem(kb['display_name'], kb['path'])
                self.kb_device_map[i] = kb['path']
        except Exception as e:
            print(f"Error loading keyboards: {e}")

    def _load_current_settings(self):
        """Load current settings into the UI"""
        # Shortcut
        current_shortcut = self.config.get_setting('primary_shortcut', 'F12')
        idx = self.shortcut_combo.findText(current_shortcut)
        if idx >= 0:
            self.shortcut_combo.setCurrentIndex(idx)

        # Model
        current_model = self.config.get_setting('model', 'large-v3')
        idx = self.model_combo.findText(current_model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)

        # Directories
        self._refresh_directories_list()

        # General
        self.always_on_top_cb.setChecked(self.config.get_setting('always_on_top', True))
        self.key_delay_spin.setValue(self.config.get_setting('key_delay', 15))

        # Audio device
        current_audio = self.config.get_setting('audio_device', None)
        for i in range(self.mic_combo.count()):
            if self.mic_combo.itemData(i) == current_audio:
                self.mic_combo.setCurrentIndex(i)
                break

        # Keyboard device
        current_kb = self.config.get_setting('keyboard_device', '')
        for i in range(self.kb_combo.count()):
            if self.kb_combo.itemData(i) == current_kb:
                self.kb_combo.setCurrentIndex(i)
                break

    def _refresh_directories_list(self):
        """Refresh the directories list"""
        self.dirs_list.clear()
        for directory in self.config.get_model_directories():
            self.dirs_list.addItem(directory)

    def _browse_directory(self):
        """Browse for a directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Model Directory",
                                                      str(Path.home()))
        if directory:
            self.new_dir_entry.setText(directory)

    def _add_directory(self):
        """Add a directory"""
        new_dir = self.new_dir_entry.text().strip()
        if not new_dir:
            QMessageBox.warning(self, "Invalid Input", "Please enter a directory path.")
            return

        if self.config.add_model_directory(new_dir):
            self._refresh_directories_list()
            self.new_dir_entry.clear()
        else:
            QMessageBox.information(self, "Already Added", "This directory is already in the list.")

    def _remove_directory(self):
        """Remove selected directory"""
        current = self.dirs_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a directory to remove.")
            return

        self.config.remove_model_directory(current.text())
        self._refresh_directories_list()

    def _refresh_models(self):
        """Refresh models after directory changes"""
        self.config.save_config()
        self._refresh_model_list()
        QMessageBox.information(self, "Models Refreshed", "Model list has been refreshed.")

    def _reset_defaults(self):
        """Reset to default settings"""
        if QMessageBox.question(self, "Reset Settings",
                                "Reset all settings to defaults?") == QMessageBox.StandardButton.Yes:
            self.config.reset_to_defaults()
            self._load_current_settings()

    def _save_settings(self):
        """Save all settings"""
        try:
            new_shortcut = self.shortcut_combo.currentText()
            old_shortcut = self.config.get_setting('primary_shortcut')

            self.config.set_setting('primary_shortcut', new_shortcut)
            self.config.set_setting('always_on_top', self.always_on_top_cb.isChecked())
            self.config.set_setting('key_delay', self.key_delay_spin.value())
            self.config.set_setting('audio_device', self.mic_combo.currentData())
            self.config.set_setting('keyboard_device', self.kb_combo.currentData())

            new_model = self.model_combo.currentText()
            if new_model != "No models found":
                self.config.set_setting('model', new_model)
                if self.whisper_manager:
                    self.whisper_manager.set_model(new_model)

            if not self.config.save_config():
                QMessageBox.critical(self, "Error", "Failed to save settings!")
                return

            # Update shortcut if changed
            if new_shortcut != old_shortcut and self.global_shortcuts:
                self.global_shortcuts.stop()
                self.global_shortcuts.update_shortcut(new_shortcut)
                self.global_shortcuts.start()

            if self.update_callback:
                self.update_callback()

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")


class WhisperTuxApp(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # Initialize core components
        self.config = ConfigManager()
        audio_device_id = self.config.get_setting('audio_device', None)
        self.audio_capture = AudioCapture(device_id=audio_device_id)
        self.whisper_manager = WhisperManager()
        self.text_injector = TextInjector(self.config)
        self.global_shortcuts = None

        # Application state
        self.is_recording = False
        self.is_processing = False

        # Signal emitter for thread-safe UI updates
        self.signals = SignalEmitter()
        self.signals.transcription_ready.connect(self._handle_transcription)
        self.signals.status_update.connect(self._update_status)
        self.signals.recording_state.connect(self._update_recording_ui)

        # Audio monitoring timer
        self.audio_timer = QTimer()
        self.audio_timer.timeout.connect(self._update_audio_level)

        # System tray
        self.tray_icon = None

        # Set up the UI
        self._setup_ui()
        self._setup_global_shortcuts()
        self._setup_system_tray()

        # Position window
        self._position_window()

    def _setup_ui(self):
        """Set up the main UI"""
        self.setWindowTitle("WhisperTux Fork - Voice Dictation")
        self.setMinimumSize(500, 680)

        # Apply stylesheet
        self.setStyleSheet(get_stylesheet())

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Status card
        status_card = self._create_status_card()
        layout.addWidget(status_card)

        # Audio level
        audio_card = self._create_audio_card()
        layout.addWidget(audio_card)

        # Transcription
        trans_card = self._create_transcription_card()
        layout.addWidget(trans_card, 1)

        # Control buttons
        controls = self._create_controls()
        layout.addWidget(controls)

        # Always on top
        if self.config.get_setting('always_on_top', True):
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

    def _create_header(self):
        """Create the header section"""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        # Logo
        try:
            logo_path = Path(__file__).parent / "assets" / "whispertux.png"
            if logo_path.exists():
                pixmap = QPixmap(str(logo_path))
                logo_label = QLabel()
                logo_label.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                                                    Qt.TransformationMode.SmoothTransformation))
                layout.addWidget(logo_label)
        except Exception as e:
            print(f"Failed to load logo: {e}")

        # Title section
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(12, 0, 0, 0)
        title_layout.setSpacing(4)

        title = QLabel("WhisperTux Fork")
        title.setObjectName("title")
        title_layout.addWidget(title)

        subtitle = QLabel("AMD GPU Support Spin")
        subtitle.setObjectName("subtitle")
        title_layout.addWidget(subtitle)

        layout.addWidget(title_widget)
        layout.addStretch()

        return header

    def _create_status_card(self):
        """Create the status display card"""
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # Header row
        header_layout = QHBoxLayout()

        section_title = QLabel("Status")
        section_title.setObjectName("section_title")
        header_layout.addWidget(section_title)

        header_layout.addStretch()

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status_ready")
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        # Info grid
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        # Model
        model_row = QHBoxLayout()
        model_label = QLabel("Model:")
        model_label.setObjectName("info_label")
        model_row.addWidget(model_label)
        self.model_display = QLabel(self.config.get_setting('model', 'large-v3'))
        self.model_display.setObjectName("info_value")
        model_row.addWidget(self.model_display)
        model_row.addStretch()
        info_layout.addLayout(model_row)

        # Shortcut
        shortcut_row = QHBoxLayout()
        shortcut_label = QLabel("Shortcut:")
        shortcut_label.setObjectName("info_label")
        shortcut_row.addWidget(shortcut_label)
        self.shortcut_display = QLabel(self.config.get_setting('primary_shortcut', 'F12'))
        self.shortcut_display.setObjectName("info_value")
        shortcut_row.addWidget(self.shortcut_display)
        shortcut_row.addStretch()
        info_layout.addLayout(shortcut_row)

        # Key delay
        delay_row = QHBoxLayout()
        delay_label = QLabel("Key Delay:")
        delay_label.setObjectName("info_label")
        delay_row.addWidget(delay_label)
        self.delay_display = QLabel(f"{self.config.get_setting('key_delay', 15)}ms")
        self.delay_display.setObjectName("info_value")
        delay_row.addWidget(self.delay_display)
        delay_row.addStretch()
        info_layout.addLayout(delay_row)

        # Microphone
        mic_row = QHBoxLayout()
        mic_label = QLabel("Microphone:")
        mic_label.setObjectName("info_label")
        mic_row.addWidget(mic_label)
        self.mic_display = QLabel(self._get_current_mic_name())
        self.mic_display.setObjectName("info_value")
        mic_row.addWidget(self.mic_display)
        mic_row.addStretch()
        info_layout.addLayout(mic_row)

        layout.addLayout(info_layout)

        # Mode selector
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Mode:")
        mode_label.setObjectName("info_label")
        mode_layout.addWidget(mode_label)

        self.mode_group = QButtonGroup(self)

        self.live_mode_btn = QRadioButton("Live Text Entry")
        self.note_mode_btn = QRadioButton("Note Entry")

        self.mode_group.addButton(self.live_mode_btn, 0)
        self.mode_group.addButton(self.note_mode_btn, 1)

        current_mode = self.config.get_setting('operation_mode', 'live_text_entry')
        if current_mode == 'live_text_entry':
            self.live_mode_btn.setChecked(True)
        else:
            self.note_mode_btn.setChecked(True)

        self.mode_group.buttonClicked.connect(self._on_mode_change)

        mode_layout.addWidget(self.live_mode_btn)
        mode_layout.addWidget(self.note_mode_btn)
        mode_layout.addStretch()

        layout.addLayout(mode_layout)

        return card

    def _create_audio_card(self):
        """Create the audio level card"""
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        title = QLabel("Audio Level")
        title.setObjectName("section_title")
        layout.addWidget(title)

        self.audio_meter = AudioLevelWidget()
        layout.addWidget(self.audio_meter)

        return card

    def _create_transcription_card(self):
        """Create the transcription text area"""
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        current_mode = self.config.get_setting('operation_mode', 'live_text_entry')
        label_text = "Notes" if current_mode == 'note_entry' else "Transcription Log"
        self.trans_title = QLabel(label_text)
        self.trans_title.setObjectName("section_title")
        layout.addWidget(self.trans_title)

        self.transcription_text = QTextEdit()
        self.transcription_text.setReadOnly(True)
        self.transcription_text.setPlaceholderText("Transcriptions will appear here...")
        layout.addWidget(self.transcription_text)

        # Buttons
        btn_layout = QHBoxLayout()

        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self._copy_transcription)
        btn_layout.addWidget(copy_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_transcription)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return card

    def _create_controls(self):
        """Create control buttons"""
        controls = QWidget()
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(0, 0, 0, 0)

        quit_btn = QPushButton("Quit")
        quit_btn.setObjectName("danger")
        quit_btn.clicked.connect(self.close)
        layout.addWidget(quit_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self._show_settings)
        layout.addWidget(settings_btn)

        layout.addStretch()

        self.record_btn = QPushButton("Start Recording")
        self.record_btn.setObjectName("primary")
        self.record_btn.setMinimumWidth(160)
        self.record_btn.setMinimumHeight(44)
        self.record_btn.clicked.connect(self._toggle_recording)
        layout.addWidget(self.record_btn)

        return controls

    def _setup_global_shortcuts(self):
        """Set up global keyboard shortcuts"""
        try:
            keyboard_device = self.config.get_setting('keyboard_device', '')
            device_path = keyboard_device if keyboard_device else None
            self.global_shortcuts = GlobalShortcuts(
                primary_key=self.config.get_setting('primary_shortcut', 'F12'),
                callback=self._toggle_recording,
                device_path=device_path
            )
            self.global_shortcuts.start()
            print("Global shortcuts initialized")
        except Exception as e:
            print(f"ERROR: Failed to setup global shortcuts: {e}")

    def _setup_system_tray(self):
        """Set up the system tray icon"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("System tray not available")
            return

        self.tray_icon = QSystemTrayIcon(self)

        # Create icon
        icon_pixmap = QPixmap(32, 32)
        icon_pixmap.fill(QColor(COLORS['primary']))
        self.tray_icon.setIcon(QIcon(icon_pixmap))

        # Create menu
        tray_menu = QMenu()

        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        toggle_action = QAction("Toggle Recording", self)
        toggle_action.triggered.connect(self._toggle_recording)
        tray_menu.addAction(toggle_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("WhisperTux Fork - Ready")
        self.tray_icon.show()

    def _position_window(self):
        """Position window in bottom-left corner"""
        screen = QApplication.primaryScreen().geometry()
        self.move(20, screen.height() - self.height() - 60)

    def _get_current_mic_name(self):
        """Get the current microphone name"""
        try:
            info = self.audio_capture.get_current_device_info()
            if info:
                name = info['name']
                if len(name) > 35:
                    name = name[:32] + "..."
                return name
        except:
            pass
        return "default"

    def _on_mode_change(self, button):
        """Handle mode change"""
        if button == self.live_mode_btn:
            self.config.set_setting('operation_mode', 'live_text_entry')
            self.trans_title.setText("Transcription Log")
        else:
            self.config.set_setting('operation_mode', 'note_entry')
            self.trans_title.setText("Notes")
        self.config.save_config()

    def _toggle_recording(self):
        """Toggle recording state"""
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start recording"""
        if self.is_recording or self.is_processing:
            return

        try:
            self.is_recording = True
            self.signals.recording_state.emit(True)

            # Start audio monitoring
            self.audio_meter.set_recording(True)
            self.audio_timer.start(50)

            def record_audio():
                try:
                    self.audio_capture.start_recording()
                except Exception as e:
                    self.signals.status_update.emit(f"Recording error: {e}")
                    self.signals.recording_state.emit(False)

            threading.Thread(target=record_audio, daemon=True).start()

        except Exception as e:
            self.is_recording = False
            self.signals.recording_state.emit(False)
            QMessageBox.critical(self, "Error", f"Failed to start recording: {e}")

    def _stop_recording(self):
        """Stop recording and process"""
        if not self.is_recording:
            return

        self.is_recording = False
        self.is_processing = True
        self.signals.recording_state.emit(False)

        # Stop audio monitoring
        self.audio_timer.stop()
        self.audio_meter.set_recording(False)

        def process_recording():
            try:
                audio_data = self.audio_capture.stop_recording()

                if audio_data is not None and len(audio_data) > 0:
                    self.signals.status_update.emit("Processing...")
                    transcription = self.whisper_manager.transcribe_audio(audio_data)
                    self.signals.transcription_ready.emit(transcription)
                else:
                    self.signals.transcription_ready.emit("")

            except Exception as e:
                self.signals.status_update.emit(f"Error: {e}")
                # Reset UI on error too
                self.signals.transcription_ready.emit("")

        threading.Thread(target=process_recording, daemon=True).start()

    def _update_audio_level(self):
        """Update audio level meter"""
        level = self.audio_capture.get_audio_level()
        self.audio_meter.set_level(level)

    def _handle_transcription(self, transcription: str):
        """Handle completed transcription"""
        # Reset processing state and update UI
        self.is_processing = False
        self._reset_record_button()

        current_mode = self.config.get_setting('operation_mode', 'live_text_entry')

        if transcription and transcription.strip():
            cleaned = transcription.strip()
            blank_indicators = ["[blank_audio]", "(blank)", "(silence)", "[silence]", "[BLANK_AUDIO]"]
            is_blank = any(indicator.lower() in cleaned.lower() for indicator in blank_indicators)

            if not is_blank:
                if current_mode == 'live_text_entry':
                    try:
                        self.text_injector.inject_text(cleaned)
                        self._update_status("Text injected")
                    except Exception:
                        self._update_status("Injection failed")
                else:
                    self.transcription_text.append(cleaned)
                    self._update_status("Note added")
            else:
                self._update_status("No speech detected")
        else:
            self._update_status("No speech detected")

    def _reset_record_button(self):
        """Reset the record button to ready state"""
        self.record_btn.setText("Start Recording")
        self.record_btn.setObjectName("primary")
        self.record_btn.setEnabled(True)
        self.record_btn.setStyle(self.record_btn.style())

    def _update_status(self, status: str):
        """Update status display"""
        self.status_label.setText(status)

        if "Recording" in status:
            self.status_label.setObjectName("status_recording")
        elif "Processing" in status:
            self.status_label.setObjectName("status_processing")
        else:
            self.status_label.setObjectName("status_ready")

        # Force style update
        self.status_label.setStyle(self.status_label.style())

        # Update tray tooltip
        if self.tray_icon:
            self.tray_icon.setToolTip(f"WhisperTux Fork - {status}")

    def _update_recording_ui(self, is_recording: bool):
        """Update UI for recording state"""
        if is_recording:
            self.record_btn.setText("Stop Recording")
            self.record_btn.setObjectName("recording")
            self._update_status("Recording...")
        elif self.is_processing:
            self.record_btn.setText("Processing...")
            self.record_btn.setEnabled(False)
            self._update_status("Processing...")
        else:
            self.record_btn.setText("Start Recording")
            self.record_btn.setObjectName("primary")
            self.record_btn.setEnabled(True)
            self._update_status("Ready")

        # Force style update
        self.record_btn.setStyle(self.record_btn.style())

    def _copy_transcription(self):
        """Copy transcription to clipboard"""
        text = self.transcription_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _clear_transcription(self):
        """Clear transcription text"""
        self.transcription_text.clear()

    def _show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self, self.config, self.global_shortcuts,
                                 self.whisper_manager, self._update_displays)
        dialog.exec()

    def _update_displays(self):
        """Update all display labels from config"""
        self.model_display.setText(self.config.get_setting('model', 'large-v3'))
        self.shortcut_display.setText(self.config.get_setting('primary_shortcut', 'F12'))
        self.delay_display.setText(f"{self.config.get_setting('key_delay', 15)}ms")
        self.mic_display.setText(self._get_current_mic_name())

        # Update always on top
        if self.config.get_setting('always_on_top', True):
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def closeEvent(self, event):
        """Handle window close"""
        try:
            if self.global_shortcuts:
                self.global_shortcuts.stop()

            if self.is_recording:
                self.audio_capture.stop_recording()

            self.audio_timer.stop()

            if self.tray_icon:
                self.tray_icon.hide()

            self.config.save_config()

        except Exception as e:
            print(f"Error during cleanup: {e}")

        event.accept()


def main():
    """Main entry point"""
    if not sys.platform.startswith('linux'):
        print("Warning: This application is designed for Linux systems")

    app = QApplication(sys.argv)
    app.setApplicationName("WhisperTux Fork")
    app.setStyle("Fusion")  # Use Fusion style for consistent look

    window = WhisperTuxApp()

    # Initialize whisper
    if not window.whisper_manager.initialize():
        QMessageBox.critical(
            None,
            "Initialization Error",
            "Failed to initialize Whisper. Please ensure whisper.cpp is built.\nRun the build scripts first."
        )
        sys.exit(1)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
