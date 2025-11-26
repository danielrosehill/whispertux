#!/usr/bin/env python3
"""
WhisperTux Fork - Voice dictation application for Linux
PySide6 GUI with modern styling and KDE Plasma integration
"""

import sys
import threading
import time
import subprocess
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame, QComboBox, QDialog,
    QScrollArea, QLineEdit, QCheckBox, QSpinBox, QMessageBox,
    QFileDialog, QListWidget, QListWidgetItem, QButtonGroup,
    QRadioButton, QGroupBox, QSizePolicy, QSystemTrayIcon, QMenu,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStackedWidget
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
from src.benchmark import (
    WhisperBenchmark, BENCHMARK_SAMPLES, BenchmarkResult, ModelSummary,
    calculate_wer, calculate_efficiency_score
)


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

        QLabel#status_paused {{
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
            color: {COLORS['text']};
            background-color: transparent;
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            margin-top: 20px;
            padding-top: 16px;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 2px 10px;
            background-color: {COLORS['primary']};
            color: {COLORS['background']};
            border-radius: 4px;
        }}

        QGroupBox QLabel {{
            color: {COLORS['text']};
        }}

        QRadioButton {{
            font-size: 13px;
            spacing: 8px;
            color: {COLORS['text']};
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

        QMessageBox {{
            background-color: {COLORS['background']};
        }}

        QMessageBox QLabel {{
            color: {COLORS['text']};
        }}
    """


class AudioFeedback:
    """Provides audio feedback beeps for recording state changes"""

    @staticmethod
    def play_start_beep():
        """Play a high-pitched beep when recording starts"""
        try:
            # High-pitched beep (1000Hz, 100ms)
            subprocess.Popen(
                ['paplay', '--raw', '--rate=44100', '--channels=1', '--format=s16le'],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ).communicate(input=AudioFeedback._generate_tone(1000, 0.1))
        except Exception:
            # Fallback to beep command or just ignore
            try:
                subprocess.run(['beep', '-f', '1000', '-l', '100'],
                             capture_output=True, timeout=1)
            except Exception:
                pass

    @staticmethod
    def play_stop_beep():
        """Play a lower-pitched beep when recording stops"""
        try:
            # Lower-pitched beep (600Hz, 150ms)
            subprocess.Popen(
                ['paplay', '--raw', '--rate=44100', '--channels=1', '--format=s16le'],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ).communicate(input=AudioFeedback._generate_tone(600, 0.15))
        except Exception:
            try:
                subprocess.run(['beep', '-f', '600', '-l', '150'],
                             capture_output=True, timeout=1)
            except Exception:
                pass

    @staticmethod
    def _generate_tone(frequency: int, duration: float) -> bytes:
        """Generate a simple sine wave tone"""
        import math
        sample_rate = 44100
        num_samples = int(sample_rate * duration)
        samples = []
        for i in range(num_samples):
            # Generate sine wave with fade in/out to avoid clicks
            t = i / sample_rate
            fade = min(i / 500, (num_samples - i) / 500, 1.0)  # Fade over ~11ms
            value = int(32767 * fade * 0.25 * math.sin(2 * math.pi * frequency * t))  # 50% quieter
            # Pack as signed 16-bit little-endian
            samples.append(value & 0xFF)
            samples.append((value >> 8) & 0xFF)
        return bytes(samples)


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
    pause_state = Signal(bool)  # True = paused, False = resumed


class BenchmarkDialog(QDialog):
    """Dialog for running model benchmarks"""

    # Signals for thread-safe UI updates
    class BenchmarkSignals(QObject):
        sample_started = Signal(int, str)  # sample_index, sample_text
        recording_started = Signal()
        recording_stopped = Signal(float)  # duration
        transcription_progress = Signal(str, int, int)  # model_name, current, total
        transcription_result = Signal(str, float, float)  # model_name, wer, time
        benchmark_complete = Signal(dict)  # summaries
        error = Signal(str)

    def __init__(self, parent, config: ConfigManager, whisper_manager: WhisperManager,
                 audio_capture: AudioCapture):
        super().__init__(parent)
        self.config = config
        self.whisper_manager = whisper_manager
        self.audio_capture = audio_capture

        self.setWindowTitle("Model Benchmark")
        self.setMinimumSize(800, 700)
        self.setModal(True)

        # Benchmark state
        self.is_running = False
        self.is_recording = False
        self.current_sample_index = 0
        self.samples = []
        self.recordings = []  # List of (audio_data, duration, sample)
        self.selected_models = []
        self.results = []
        self.summaries = {}

        # Signals
        self.signals = self.BenchmarkSignals()
        self.signals.sample_started.connect(self._on_sample_started)
        self.signals.recording_started.connect(self._on_recording_started)
        self.signals.recording_stopped.connect(self._on_recording_stopped)
        self.signals.transcription_progress.connect(self._on_transcription_progress)
        self.signals.transcription_result.connect(self._on_transcription_result)
        self.signals.benchmark_complete.connect(self._on_benchmark_complete)
        self.signals.error.connect(self._on_error)

        # Audio monitoring timer
        self.audio_timer = QTimer()
        self.audio_timer.timeout.connect(self._update_audio_level)

        self._setup_ui()
        self._load_models()

    def _setup_ui(self):
        """Set up the benchmark dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Model Benchmark")
        title.setObjectName("title")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['primary']};")
        layout.addWidget(title)

        subtitle = QLabel("Test your models to find the optimal balance between accuracy and speed")
        subtitle.setStyleSheet(f"color: {COLORS['text_dim']}; margin-bottom: 10px;")
        layout.addWidget(subtitle)

        # Stacked widget for different stages
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        # Page 0: Setup
        self.setup_page = self._create_setup_page()
        self.stack.addWidget(self.setup_page)

        # Page 1: Recording
        self.recording_page = self._create_recording_page()
        self.stack.addWidget(self.recording_page)

        # Page 2: Processing
        self.processing_page = self._create_processing_page()
        self.stack.addWidget(self.processing_page)

        # Page 3: Results
        self.results_page = self._create_results_page()
        self.stack.addWidget(self.results_page)

        # Bottom buttons
        self.button_layout = QHBoxLayout()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.button_layout.addWidget(self.cancel_btn)

        self.button_layout.addStretch()

        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self._go_back)
        self.back_btn.setVisible(False)
        self.button_layout.addWidget(self.back_btn)

        self.next_btn = QPushButton("Start Benchmark")
        self.next_btn.setObjectName("primary")
        self.next_btn.clicked.connect(self._on_next)
        self.button_layout.addWidget(self.next_btn)

        layout.addLayout(self.button_layout)

    def _create_setup_page(self):
        """Create the setup/configuration page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        # Model selection
        models_group = QGroupBox("Select Models to Test")
        models_layout = QVBoxLayout(models_group)

        self.models_list = QListWidget()
        self.models_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.models_list.setMaximumHeight(200)
        models_layout.addWidget(self.models_list)

        select_btns = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._select_all_models(True))
        select_btns.addWidget(select_all_btn)

        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(lambda: self._select_all_models(False))
        select_btns.addWidget(select_none_btn)

        select_btns.addStretch()
        models_layout.addLayout(select_btns)

        layout.addWidget(models_group)

        # Sample count selection
        samples_group = QGroupBox("Number of Samples")
        samples_layout = QHBoxLayout(samples_group)

        samples_layout.addWidget(QLabel("Record"))
        self.samples_spin = QSpinBox()
        self.samples_spin.setRange(1, 10)
        self.samples_spin.setValue(3)
        samples_layout.addWidget(self.samples_spin)
        samples_layout.addWidget(QLabel("text samples (each ~25 seconds)"))
        samples_layout.addStretch()

        layout.addWidget(samples_group)

        # Instructions
        instructions = QLabel(
            "How it works:\n"
            "1. You'll see text samples to read aloud\n"
            "2. Press the Record button and read the text\n"
            "3. Each recording is tested against all selected models\n"
            "4. Results show WER (accuracy) and inference time for each model\n"
            "5. A recommendation is provided based on the efficiency score"
        )
        instructions.setStyleSheet(f"color: {COLORS['text_dim']}; padding: 10px; "
                                   f"background-color: {COLORS['surface']}; border-radius: 8px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        layout.addStretch()
        return page

    def _create_recording_page(self):
        """Create the recording page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        # Progress
        progress_layout = QHBoxLayout()
        self.sample_progress_label = QLabel("Sample 1 of 3")
        self.sample_progress_label.setStyleSheet(f"font-size: 14px; color: {COLORS['text']};")
        progress_layout.addWidget(self.sample_progress_label)
        progress_layout.addStretch()
        layout.addLayout(progress_layout)

        # Category label
        self.category_label = QLabel("Category: everyday_narrative")
        self.category_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        layout.addWidget(self.category_label)

        # Text to read
        text_group = QGroupBox("Read This Text Aloud")
        text_layout = QVBoxLayout(text_group)

        self.sample_text = QTextEdit()
        self.sample_text.setReadOnly(True)
        self.sample_text.setMinimumHeight(150)
        self.sample_text.setStyleSheet(f"""
            QTextEdit {{
                font-size: 16px;
                line-height: 1.6;
                padding: 15px;
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['primary']};
                border-radius: 8px;
            }}
        """)
        text_layout.addWidget(self.sample_text)

        layout.addWidget(text_group)

        # Audio level meter
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Audio Level:"))
        self.benchmark_audio_meter = AudioLevelWidget()
        level_layout.addWidget(self.benchmark_audio_meter, 1)
        layout.addLayout(level_layout)

        # Recording status
        self.recording_status = QLabel("Press Record when ready")
        self.recording_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recording_status.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text']};")
        layout.addWidget(self.recording_status)

        # Record button
        self.record_btn = QPushButton("⏺ Start Recording")
        self.record_btn.setMinimumHeight(50)
        self.record_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 18px;
                background-color: {COLORS['success']};
                color: {COLORS['background']};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #8bd49a;
            }}
        """)
        self.record_btn.clicked.connect(self._toggle_recording)
        layout.addWidget(self.record_btn)

        # Recorded duration display
        self.duration_label = QLabel("")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duration_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        layout.addWidget(self.duration_label)

        layout.addStretch()
        return page

    def _create_processing_page(self):
        """Create the processing/transcription page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        # Status
        self.processing_status = QLabel("Running transcriptions...")
        self.processing_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.processing_status.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['warning']};")
        layout.addWidget(self.processing_status)

        # Progress bar
        self.processing_progress = QProgressBar()
        self.processing_progress.setMinimum(0)
        self.processing_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {COLORS['border']};
                border-radius: 5px;
                text-align: center;
                background-color: {COLORS['surface']};
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['primary']};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.processing_progress)

        # Current model being tested
        self.current_model_label = QLabel("Testing: ")
        self.current_model_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        layout.addWidget(self.current_model_label)

        # Live results table
        self.live_results_table = QTableWidget()
        self.live_results_table.setColumnCount(4)
        self.live_results_table.setHorizontalHeaderLabels(["Model", "Sample", "WER", "Time (s)"])
        self.live_results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.live_results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.live_results_table, 1)

        return page

    def _create_results_page(self):
        """Create the results page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        # Recommendation card
        self.recommendation_card = QFrame()
        self.recommendation_card.setObjectName("card")
        self.recommendation_card.setStyleSheet(f"""
            QFrame#card {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['success']};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        rec_layout = QVBoxLayout(self.recommendation_card)

        rec_title = QLabel("⭐ Recommended Model")
        rec_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['success']};")
        rec_layout.addWidget(rec_title)

        self.recommendation_model = QLabel("")
        self.recommendation_model.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['text']};")
        rec_layout.addWidget(self.recommendation_model)

        self.recommendation_reason = QLabel("")
        self.recommendation_reason.setWordWrap(True)
        self.recommendation_reason.setStyleSheet(f"color: {COLORS['text_dim']};")
        rec_layout.addWidget(self.recommendation_reason)

        layout.addWidget(self.recommendation_card)

        # Results table
        results_label = QLabel("Full Results")
        results_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['text']};")
        layout.addWidget(results_label)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["Rank", "Model", "WER", "RTF", "Efficiency"])
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.results_table, 1)

        # Legend
        legend = QLabel(
            "WER = Word Error Rate (lower is better) | "
            "RTF = Real-Time Factor (< 1.0 = faster than real-time) | "
            "Efficiency = Combined score (higher is better)"
        )
        legend.setWordWrap(True)
        legend.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
        layout.addWidget(legend)

        # Action buttons
        action_layout = QHBoxLayout()

        self.apply_model_btn = QPushButton("Apply Recommended Model")
        self.apply_model_btn.setObjectName("primary")
        self.apply_model_btn.clicked.connect(self._apply_recommended_model)
        action_layout.addWidget(self.apply_model_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        return page

    def _load_models(self):
        """Load available models into the list"""
        self.models_list.clear()
        models = self.whisper_manager.get_available_models()

        for model in models:
            item = QListWidgetItem(model)
            item.setSelected(True)  # Select all by default
            self.models_list.addItem(item)

    def _select_all_models(self, select: bool):
        """Select or deselect all models"""
        for i in range(self.models_list.count()):
            self.models_list.item(i).setSelected(select)

    def _on_next(self):
        """Handle next button click"""
        current_page = self.stack.currentIndex()

        if current_page == 0:  # Setup page
            self._start_benchmark()
        elif current_page == 1:  # Recording page
            if self.current_sample_index < len(self.samples) - 1:
                self._next_sample()
            else:
                self._start_processing()
        elif current_page == 3:  # Results page
            self.accept()

    def _go_back(self):
        """Go back to previous page"""
        current_page = self.stack.currentIndex()
        if current_page > 0:
            self.stack.setCurrentIndex(current_page - 1)
            self._update_buttons()

    def _on_cancel(self):
        """Handle cancel button"""
        if self.is_recording:
            self.audio_capture.stop_recording()
            self.audio_timer.stop()
            self.is_recording = False

        self.is_running = False
        self.reject()

    def _update_buttons(self):
        """Update button states based on current page"""
        current_page = self.stack.currentIndex()

        if current_page == 0:  # Setup
            self.back_btn.setVisible(False)
            self.next_btn.setText("Start Benchmark")
            self.next_btn.setEnabled(True)
            self.cancel_btn.setText("Cancel")
        elif current_page == 1:  # Recording
            self.back_btn.setVisible(False)  # Can't go back during recording
            if self.current_sample_index < len(self.samples) - 1:
                self.next_btn.setText("Next Sample")
            else:
                self.next_btn.setText("Run Transcriptions")
            self.next_btn.setEnabled(len(self.recordings) > self.current_sample_index)
            self.cancel_btn.setText("Cancel")
        elif current_page == 2:  # Processing
            self.back_btn.setVisible(False)
            self.next_btn.setVisible(False)
            self.cancel_btn.setText("Cancel")
        elif current_page == 3:  # Results
            self.back_btn.setVisible(False)
            self.next_btn.setText("Close")
            self.next_btn.setVisible(True)
            self.next_btn.setEnabled(True)
            self.cancel_btn.setVisible(False)

    def _start_benchmark(self):
        """Start the benchmark process"""
        # Get selected models
        self.selected_models = [
            self.models_list.item(i).text()
            for i in range(self.models_list.count())
            if self.models_list.item(i).isSelected()
        ]

        if not self.selected_models:
            QMessageBox.warning(self, "No Models", "Please select at least one model to test.")
            return

        # Get samples
        num_samples = self.samples_spin.value()
        import random
        self.samples = BENCHMARK_SAMPLES.copy()
        random.shuffle(self.samples)
        self.samples = self.samples[:num_samples]

        # Reset state
        self.recordings = []
        self.results = []
        self.current_sample_index = 0
        self.is_running = True

        # Switch to recording page
        self.stack.setCurrentIndex(1)
        self._show_current_sample()
        self._update_buttons()

    def _show_current_sample(self):
        """Display the current sample to record"""
        if self.current_sample_index >= len(self.samples):
            return

        sample = self.samples[self.current_sample_index]

        self.sample_progress_label.setText(
            f"Sample {self.current_sample_index + 1} of {len(self.samples)}"
        )
        self.category_label.setText(f"Category: {sample['category']}")
        self.sample_text.setText(sample['text'])
        self.recording_status.setText("Press Record when ready")
        self.recording_status.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text']};")
        self.duration_label.setText(f"Estimated reading time: ~{sample['estimated_seconds']} seconds")

        # Reset record button
        self.record_btn.setText("⏺ Start Recording")
        self.record_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 18px;
                background-color: {COLORS['success']};
                color: {COLORS['background']};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #8bd49a;
            }}
        """)

        # Disable next until recorded
        self.next_btn.setEnabled(len(self.recordings) > self.current_sample_index)

    def _toggle_recording(self):
        """Toggle recording state"""
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start recording audio"""
        self.is_recording = True

        # Update UI
        self.record_btn.setText("⏹ Stop Recording")
        self.record_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 18px;
                background-color: {COLORS['error']};
                color: {COLORS['background']};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #e57a96;
            }}
        """)
        self.recording_status.setText("Recording...")
        self.recording_status.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['error']};")

        # Start audio capture
        self.benchmark_audio_meter.set_recording(True)
        self.audio_timer.start(50)

        def do_record():
            try:
                self.audio_capture.start_recording()
            except Exception as e:
                self.signals.error.emit(str(e))

        threading.Thread(target=do_record, daemon=True).start()

    def _stop_recording(self):
        """Stop recording and save the audio"""
        self.is_recording = False

        # Stop audio capture
        self.audio_timer.stop()
        self.benchmark_audio_meter.set_recording(False)

        def process_recording():
            try:
                audio_data = self.audio_capture.stop_recording()

                if audio_data is not None and len(audio_data) > 0:
                    duration = len(audio_data) / 16000.0
                    sample = self.samples[self.current_sample_index]

                    self.recordings.append({
                        'audio_data': audio_data,
                        'duration': duration,
                        'sample': sample
                    })

                    self.signals.recording_stopped.emit(duration)
                else:
                    self.signals.error.emit("No audio captured")

            except Exception as e:
                self.signals.error.emit(str(e))

        threading.Thread(target=process_recording, daemon=True).start()

        # Update UI immediately
        self.record_btn.setText("⏺ Re-record")
        self.record_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 18px;
                background-color: {COLORS['warning']};
                color: {COLORS['background']};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #e5d09e;
            }}
        """)
        self.recording_status.setText("Processing...")
        self.recording_status.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['warning']};")

    def _update_audio_level(self):
        """Update the audio level meter"""
        level = self.audio_capture.get_audio_level()
        self.benchmark_audio_meter.set_level(level)

    def _on_recording_stopped(self, duration: float):
        """Handle recording stopped"""
        self.recording_status.setText(f"Recorded {duration:.1f} seconds")
        self.recording_status.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['success']};")
        self.duration_label.setText(f"Recording complete: {duration:.1f}s")

        # Enable next button
        self.next_btn.setEnabled(True)

    def _next_sample(self):
        """Move to the next sample"""
        self.current_sample_index += 1
        self._show_current_sample()
        self._update_buttons()

    def _start_processing(self):
        """Start processing all recordings through all models"""
        self.stack.setCurrentIndex(2)
        self._update_buttons()

        # Clear live results table
        self.live_results_table.setRowCount(0)

        # Calculate total operations
        total_ops = len(self.recordings) * len(self.selected_models)
        self.processing_progress.setMaximum(total_ops)
        self.processing_progress.setValue(0)

        def run_transcriptions():
            import time
            operation_count = 0
            all_results = []

            for model in self.selected_models:
                self.signals.transcription_progress.emit(model, 0, len(self.recordings))

                # Switch model
                if not self.whisper_manager.set_model(model):
                    continue

                for rec in self.recordings:
                    if not self.is_running:
                        return

                    sample = rec['sample']
                    audio_data = rec['audio_data']
                    duration = rec['duration']

                    # Time the transcription
                    start_time = time.perf_counter()
                    transcribed = self.whisper_manager.transcribe_audio(audio_data)
                    end_time = time.perf_counter()

                    inference_time = end_time - start_time
                    wer = calculate_wer(sample['text'], transcribed)
                    rtf = inference_time / duration if duration > 0 else 0

                    result = BenchmarkResult(
                        model_name=model,
                        sample_id=sample['id'],
                        reference_text=sample['text'],
                        transcribed_text=transcribed,
                        word_error_rate=wer,
                        inference_time_seconds=inference_time,
                        audio_duration_seconds=duration,
                        real_time_factor=rtf,
                        timestamp=""
                    )
                    all_results.append(result)

                    operation_count += 1
                    self.signals.transcription_result.emit(model, wer, inference_time)

            # Calculate summaries
            summaries = self._calculate_summaries(all_results)
            self.results = all_results
            self.summaries = summaries

            self.signals.benchmark_complete.emit(summaries)

        self.is_running = True
        threading.Thread(target=run_transcriptions, daemon=True).start()

    def _calculate_summaries(self, results):
        """Calculate summary statistics for each model"""
        import numpy as np
        from dataclasses import asdict

        by_model = {}
        for r in results:
            if r.model_name not in by_model:
                by_model[r.model_name] = []
            by_model[r.model_name].append(r)

        summaries = {}

        for model_name, model_results in by_model.items():
            wers = [r.word_error_rate for r in model_results]
            times = [r.inference_time_seconds for r in model_results]
            rtfs = [r.real_time_factor for r in model_results]
            durations = [r.audio_duration_seconds for r in model_results]

            avg_wer = np.mean(wers)
            avg_time = np.mean(times)
            avg_rtf = np.mean(rtfs)
            avg_duration = np.mean(durations)

            efficiency = calculate_efficiency_score(avg_wer, avg_time, avg_duration)

            summaries[model_name] = ModelSummary(
                model_name=model_name,
                average_wer=avg_wer,
                std_wer=np.std(wers) if len(wers) > 1 else 0.0,
                average_inference_time=avg_time,
                std_inference_time=np.std(times) if len(times) > 1 else 0.0,
                average_rtf=avg_rtf,
                samples_tested=len(model_results),
                efficiency_score=efficiency,
                recommendation_rank=0
            )

        # Rank by efficiency
        ranked = sorted(summaries.values(), key=lambda s: s.efficiency_score, reverse=True)
        for i, summary in enumerate(ranked, 1):
            summaries[summary.model_name].recommendation_rank = i

        return summaries

    def _on_sample_started(self, index: int, text: str):
        """Handle sample started signal"""
        pass

    def _on_recording_started(self):
        """Handle recording started signal"""
        pass

    def _on_transcription_progress(self, model: str, current: int, total: int):
        """Handle transcription progress"""
        self.current_model_label.setText(f"Testing: {model}")
        self.processing_status.setText(f"Testing {model}...")

    def _on_transcription_result(self, model: str, wer: float, time_s: float):
        """Handle individual transcription result"""
        # Add to live results table
        row = self.live_results_table.rowCount()
        self.live_results_table.insertRow(row)

        self.live_results_table.setItem(row, 0, QTableWidgetItem(model))
        self.live_results_table.setItem(row, 1, QTableWidgetItem(
            f"Sample {(row % len(self.recordings)) + 1}"
        ))
        self.live_results_table.setItem(row, 2, QTableWidgetItem(f"{wer:.1%}"))
        self.live_results_table.setItem(row, 3, QTableWidgetItem(f"{time_s:.2f}"))

        # Update progress
        current = self.processing_progress.value() + 1
        self.processing_progress.setValue(current)

        # Scroll to bottom
        self.live_results_table.scrollToBottom()

    def _on_benchmark_complete(self, summaries: dict):
        """Handle benchmark completion"""
        self.is_running = False

        # Switch to results page
        self.stack.setCurrentIndex(3)
        self._update_buttons()

        # Populate results table
        self.results_table.setRowCount(0)
        ranked = sorted(summaries.values(), key=lambda s: s.recommendation_rank)

        for summary in ranked:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)

            rank_item = QTableWidgetItem(str(summary.recommendation_rank))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 0, rank_item)

            self.results_table.setItem(row, 1, QTableWidgetItem(summary.model_name))

            wer_item = QTableWidgetItem(f"{summary.average_wer:.1%}")
            wer_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 2, wer_item)

            rtf_item = QTableWidgetItem(f"{summary.average_rtf:.2f}x")
            rtf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 3, rtf_item)

            eff_item = QTableWidgetItem(f"{summary.efficiency_score:.3f}")
            eff_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 4, eff_item)

            # Highlight best row
            if summary.recommendation_rank == 1:
                for col in range(5):
                    item = self.results_table.item(row, col)
                    item.setBackground(QColor(COLORS['success']))
                    item.setForeground(QColor(COLORS['background']))

        # Update recommendation card
        if ranked:
            best = ranked[0]
            self.recommendation_model.setText(best.model_name)
            self.recommendation_reason.setText(
                f"Efficiency Score: {best.efficiency_score:.3f}\n"
                f"Word Error Rate: {best.average_wer:.1%}\n"
                f"Real-Time Factor: {best.average_rtf:.2f}x "
                f"({best.average_inference_time:.2f}s average)"
            )
            self._recommended_model = best.model_name

    def _on_error(self, error: str):
        """Handle error signal"""
        QMessageBox.critical(self, "Error", f"Benchmark error: {error}")

    def _apply_recommended_model(self):
        """Apply the recommended model as the current model"""
        if hasattr(self, '_recommended_model'):
            self.config.set_setting('model', self._recommended_model)
            self.whisper_manager.set_model(self._recommended_model)
            self.config.save_config()
            QMessageBox.information(
                self, "Model Applied",
                f"'{self._recommended_model}' is now your active model."
            )


class SettingsDialog(QDialog):
    """Settings dialog for WhisperTux"""

    def __init__(self, parent, config: ConfigManager, global_shortcuts: GlobalShortcuts,
                 whisper_manager: WhisperManager, update_callback, audio_capture: AudioCapture = None):
        super().__init__(parent)
        self.config = config
        self.global_shortcuts = global_shortcuts
        self.whisper_manager = whisper_manager
        self.update_callback = update_callback
        self.audio_capture = audio_capture
        self.parent_window = parent

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

        button_layout.addStretch()

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_shortcuts_section(self):
        """Create shortcuts configuration section with multiple shortcut support"""
        group = QGroupBox("Global Shortcuts")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Get current shortcuts
        shortcuts = self.config.get_all_shortcuts()

        # Conflict warning label (hidden by default)
        self.shortcut_conflict_label = QLabel("")
        self.shortcut_conflict_label.setStyleSheet(f"color: {COLORS['error']}; font-weight: bold;")
        self.shortcut_conflict_label.setVisible(False)
        layout.addWidget(self.shortcut_conflict_label)

        # Store combo boxes for validation
        self.shortcut_combos = {}

        # Toggle shortcut (main shortcut)
        toggle_layout = QHBoxLayout()
        toggle_layout.addWidget(QLabel("Toggle (Start/Stop):"))
        self.toggle_shortcut_combo = QComboBox()
        self.toggle_shortcut_combo.addItems(self._get_shortcut_options())
        self.toggle_shortcut_combo.setCurrentText(shortcuts.get('toggle', 'F13'))
        self.toggle_shortcut_combo.currentTextChanged.connect(lambda: self._validate_shortcuts())
        toggle_layout.addWidget(self.toggle_shortcut_combo)
        toggle_layout.addStretch()
        layout.addLayout(toggle_layout)
        self.shortcut_combos['toggle'] = self.toggle_shortcut_combo

        # Helper text
        helper_label = QLabel("Optional: Define separate keys for individual actions")
        helper_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; margin-top: 8px;")
        layout.addWidget(helper_label)

        # Start shortcut
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start Only:"))
        self.start_shortcut_combo = QComboBox()
        self.start_shortcut_combo.addItem("(None)", "")
        self.start_shortcut_combo.addItems(self._get_shortcut_options())
        if shortcuts.get('start'):
            idx = self.start_shortcut_combo.findText(shortcuts.get('start'))
            if idx >= 0:
                self.start_shortcut_combo.setCurrentIndex(idx)
        self.start_shortcut_combo.currentTextChanged.connect(lambda: self._validate_shortcuts())
        start_layout.addWidget(self.start_shortcut_combo)
        start_layout.addStretch()
        layout.addLayout(start_layout)
        self.shortcut_combos['start'] = self.start_shortcut_combo

        # Stop shortcut
        stop_layout = QHBoxLayout()
        stop_layout.addWidget(QLabel("Stop Only:"))
        self.stop_shortcut_combo = QComboBox()
        self.stop_shortcut_combo.addItem("(None)", "")
        self.stop_shortcut_combo.addItems(self._get_shortcut_options())
        if shortcuts.get('stop'):
            idx = self.stop_shortcut_combo.findText(shortcuts.get('stop'))
            if idx >= 0:
                self.stop_shortcut_combo.setCurrentIndex(idx)
        self.stop_shortcut_combo.currentTextChanged.connect(lambda: self._validate_shortcuts())
        stop_layout.addWidget(self.stop_shortcut_combo)
        stop_layout.addStretch()
        layout.addLayout(stop_layout)
        self.shortcut_combos['stop'] = self.stop_shortcut_combo

        # Pause shortcut
        pause_layout = QHBoxLayout()
        pause_layout.addWidget(QLabel("Pause:"))
        self.pause_shortcut_combo = QComboBox()
        self.pause_shortcut_combo.addItem("(None)", "")
        self.pause_shortcut_combo.addItems(self._get_shortcut_options())
        if shortcuts.get('pause'):
            idx = self.pause_shortcut_combo.findText(shortcuts.get('pause'))
            if idx >= 0:
                self.pause_shortcut_combo.setCurrentIndex(idx)
        self.pause_shortcut_combo.currentTextChanged.connect(lambda: self._validate_shortcuts())
        pause_layout.addWidget(self.pause_shortcut_combo)
        pause_layout.addStretch()
        layout.addLayout(pause_layout)
        self.shortcut_combos['pause'] = self.pause_shortcut_combo

        # Legacy reference (for backward compatibility display)
        self.shortcut_combo = self.toggle_shortcut_combo

        return group

    def _validate_shortcuts(self):
        """Validate shortcuts for conflicts and update UI"""
        # Collect all non-empty shortcuts
        shortcuts = {}
        for name, combo in self.shortcut_combos.items():
            key = combo.currentText()
            if key and key != "(None)":
                shortcuts[name] = key.lower().strip()

        # Find conflicts
        seen_keys = {}
        conflicts = []
        for name, key in shortcuts.items():
            if key in seen_keys:
                conflicts.append(f"'{name}' conflicts with '{seen_keys[key]}' (both use {key.upper()})")
            else:
                seen_keys[key] = name

        # Update UI
        if conflicts:
            self.shortcut_conflict_label.setText("⚠ " + "; ".join(conflicts))
            self.shortcut_conflict_label.setVisible(True)
            return False
        else:
            self.shortcut_conflict_label.setVisible(False)
            return True

    def _create_model_section(self):
        """Create model configuration section"""
        group = QGroupBox("Whisper Model")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(280)
        self._refresh_model_list()
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        layout.addLayout(model_layout)

        # Model path display
        path_layout = QHBoxLayout()
        path_label = QLabel("Path:")
        path_label.setObjectName("info_label")
        path_layout.addWidget(path_label)
        self.model_path_label = QLabel("")
        self.model_path_label.setObjectName("info_label")
        self.model_path_label.setWordWrap(True)
        self.model_path_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
        path_layout.addWidget(self.model_path_label, 1)
        layout.addLayout(path_layout)

        # Browse for custom model
        custom_layout = QHBoxLayout()
        self.custom_model_entry = QLineEdit()
        self.custom_model_entry.setPlaceholderText("Or browse for a custom .bin model file...")
        custom_layout.addWidget(self.custom_model_entry)

        browse_model_btn = QPushButton("Browse")
        browse_model_btn.clicked.connect(self._browse_custom_model)
        custom_layout.addWidget(browse_model_btn)
        layout.addLayout(custom_layout)

        # Add custom model button
        add_custom_btn = QPushButton("Add Custom Model")
        add_custom_btn.clicked.connect(self._add_custom_model)
        layout.addWidget(add_custom_btn)

        # Benchmark button
        benchmark_btn = QPushButton("🔬 Run Model Benchmark")
        benchmark_btn.setToolTip("Test all models to find the best one for your hardware")
        benchmark_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: {COLORS['background']};
                font-weight: bold;
                padding: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_dark']};
            }}
        """)
        benchmark_btn.clicked.connect(self._show_benchmark_dialog)
        layout.addWidget(benchmark_btn)

        return group

    def _show_benchmark_dialog(self):
        """Show the benchmark dialog"""
        if self.audio_capture is None:
            QMessageBox.warning(
                self, "Audio Not Available",
                "Audio capture is not available. Cannot run benchmark."
            )
            return

        dialog = BenchmarkDialog(
            self, self.config, self.whisper_manager, self.audio_capture
        )
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            # Refresh the model list and update display
            self._refresh_model_list()
            current_model = self.config.get_setting('model')
            idx = self.model_combo.findText(current_model)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

    def _on_model_changed(self, model_name: str):
        """Update model path display when selection changes"""
        if not model_name or model_name == "No models found":
            self.model_path_label.setText("")
            return

        # Get path from whisper manager's cached paths
        if self.whisper_manager and hasattr(self.whisper_manager, '_model_paths'):
            path = self.whisper_manager._model_paths.get(model_name, "")
            if path:
                # Truncate long paths for display
                display_path = path
                if len(display_path) > 60:
                    display_path = "..." + display_path[-57:]
                self.model_path_label.setText(display_path)
                self.model_path_label.setToolTip(path)
            else:
                self.model_path_label.setText("")

    def _browse_custom_model(self):
        """Browse for a custom model file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Whisper Model",
            str(Path.home() / "ai" / "models"),
            "Whisper Models (*.bin *.ggml);;All Files (*)"
        )
        if file_path:
            self.custom_model_entry.setText(file_path)

    def _add_custom_model(self):
        """Add a custom model to the list"""
        custom_path = self.custom_model_entry.text().strip()
        if not custom_path:
            QMessageBox.warning(self, "No Path", "Please enter or browse for a model file path.")
            return

        custom_path = Path(custom_path).expanduser()
        if not custom_path.exists():
            QMessageBox.warning(self, "File Not Found", f"Model file not found:\n{custom_path}")
            return

        if not custom_path.suffix in ['.bin', '.ggml']:
            QMessageBox.warning(self, "Invalid File", "Please select a .bin or .ggml model file.")
            return

        # Add to whisper manager's model paths
        custom_name = f"[Custom] {custom_path.stem}"
        if self.whisper_manager:
            if not hasattr(self.whisper_manager, '_model_paths'):
                self.whisper_manager._model_paths = {}
            self.whisper_manager._model_paths[custom_name] = str(custom_path)

        # Refresh the dropdown and select the new model
        self._refresh_model_list()
        idx = self.model_combo.findText(custom_name)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)

        self.custom_model_entry.clear()
        QMessageBox.information(self, "Model Added", f"Custom model added:\n{custom_name}")

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

        # Audio feedback
        self.audio_feedback_cb = QCheckBox("Play audio feedback when recording starts/stops")
        layout.addWidget(self.audio_feedback_cb)

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
        # Shortcuts are already loaded in _create_shortcuts_section
        # Just validate them
        self._validate_shortcuts()

        # Model
        current_model = self.config.get_setting('model', 'large-v3')
        idx = self.model_combo.findText(current_model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        # Trigger path display update
        self._on_model_changed(self.model_combo.currentText())

        # Directories
        self._refresh_directories_list()

        # General
        self.always_on_top_cb.setChecked(self.config.get_setting('always_on_top', True))
        self.audio_feedback_cb.setChecked(self.config.get_setting('audio_feedback', True))
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

    def _save_settings(self):
        """Save all settings"""
        try:
            # Validate shortcuts first
            if not self._validate_shortcuts():
                QMessageBox.warning(self, "Shortcut Conflict",
                                   "Please resolve the shortcut conflicts before saving.")
                return

            # Collect new shortcuts
            new_shortcuts = {}
            for name, combo in self.shortcut_combos.items():
                key = combo.currentText()
                if key == "(None)":
                    key = ""
                new_shortcuts[name] = key

            # Get old shortcuts for comparison
            old_shortcuts = self.config.get_all_shortcuts()

            # Save each shortcut
            for name, key in new_shortcuts.items():
                self.config.set_shortcut(name, key)

            # Legacy compatibility
            self.config.set_setting('primary_shortcut', new_shortcuts.get('toggle', 'F13'))

            # Save other settings
            self.config.set_setting('always_on_top', self.always_on_top_cb.isChecked())
            self.config.set_setting('audio_feedback', self.audio_feedback_cb.isChecked())
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

            # Update shortcuts if changed
            shortcuts_changed = new_shortcuts != old_shortcuts
            if shortcuts_changed and self.global_shortcuts:
                self.global_shortcuts.stop()
                # Update each shortcut
                for name, key in new_shortcuts.items():
                    self.global_shortcuts.update_shortcut_by_name(name, key)
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
        self.is_paused = False
        self.is_processing = False

        # Signal emitter for thread-safe UI updates
        self.signals = SignalEmitter()
        self.signals.transcription_ready.connect(self._handle_transcription)
        self.signals.status_update.connect(self._update_status)
        self.signals.recording_state.connect(self._update_recording_ui)
        self.signals.pause_state.connect(self._update_pause_ui)

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

        trans_title = QLabel("Transcription")
        trans_title.setObjectName("section_title")
        layout.addWidget(trans_title)

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
        """Create control buttons with icon symbols"""
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

        # Pause button (only visible during recording)
        # Using Unicode pause symbol: ⏸ (U+23F8)
        self.pause_btn = QPushButton("⏸")
        self.pause_btn.setToolTip("Pause recording")
        self.pause_btn.setMinimumWidth(44)
        self.pause_btn.setMinimumHeight(44)
        self.pause_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 20px;
                background-color: {COLORS['surface_light']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
            }}
        """)
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.pause_btn.setVisible(False)  # Hidden until recording starts
        layout.addWidget(self.pause_btn)

        # Record button using Unicode symbols
        # ⏺ (U+23FA) for record, ⏹ (U+23F9) for stop
        self.record_btn = QPushButton("⏺")
        self.record_btn.setToolTip("Start recording")
        self.record_btn.setObjectName("primary")
        self.record_btn.setMinimumWidth(60)
        self.record_btn.setMinimumHeight(44)
        self.record_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 24px;
            }}
            QPushButton#primary {{
                background-color: {COLORS['success']};
                color: {COLORS['background']};
            }}
            QPushButton#primary:hover {{
                background-color: #8bd49a;
            }}
            QPushButton#recording {{
                background-color: {COLORS['error']};
                color: {COLORS['background']};
            }}
            QPushButton#recording:hover {{
                background-color: #e57a96;
            }}
        """)
        self.record_btn.clicked.connect(self._toggle_recording)
        layout.addWidget(self.record_btn)

        return controls

    def _setup_global_shortcuts(self):
        """Set up global keyboard shortcuts"""
        try:
            keyboard_device = self.config.get_setting('keyboard_device', '')
            device_path = keyboard_device if keyboard_device else None

            # Get all shortcut configurations
            shortcuts = self.config.get_all_shortcuts()

            self.global_shortcuts = GlobalShortcuts(
                primary_key=self.config.get_setting('primary_shortcut', 'F13'),
                callback=self._toggle_recording,
                device_path=device_path,
                toggle_key=shortcuts.get('toggle', ''),
                start_key=shortcuts.get('start', ''),
                stop_key=shortcuts.get('stop', ''),
                pause_key=shortcuts.get('pause', ''),
                toggle_callback=self._toggle_recording,
                start_callback=self._start_recording,
                stop_callback=self._stop_recording,
                pause_callback=self._toggle_pause,
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

        # Create tray icons for different states
        self._create_tray_icons()
        self.tray_icon.setIcon(self.tray_icon_idle)

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

    def _create_tray_icons(self):
        """Create icons for different tray states"""
        # Recording icon - red filled circle
        pixmap_rec = QPixmap(32, 32)
        pixmap_rec.fill(Qt.transparent)
        painter = QPainter(pixmap_rec)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#ff5555"))  # Red color
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 28, 28)
        painter.end()
        self.tray_icon_recording = QIcon(pixmap_rec)

        # Idle icon - blue filled circle (visible on any background)
        pixmap_idle = QPixmap(32, 32)
        pixmap_idle.fill(Qt.transparent)
        painter = QPainter(pixmap_idle)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(COLORS['primary']))  # Blue color
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 28, 28)
        painter.end()
        self.tray_icon_idle = QIcon(pixmap_idle)

    def _update_tray_icon(self, is_recording: bool):
        """Update the system tray icon based on recording state"""
        if not self.tray_icon:
            return

        if is_recording:
            self.tray_icon.setIcon(self.tray_icon_recording)
        else:
            self.tray_icon.setIcon(self.tray_icon_idle)

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

    def _toggle_recording(self):
        """Toggle recording state"""
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _toggle_pause(self):
        """Toggle pause state during recording"""
        if not self.is_recording:
            return

        self.is_paused = self.audio_capture.toggle_pause()
        self.signals.pause_state.emit(self.is_paused)

    def _start_recording(self):
        """Start recording"""
        if self.is_recording or self.is_processing:
            return

        try:
            self.is_recording = True
            self.signals.recording_state.emit(True)

            # Play start beep if enabled
            if self.config.get_setting('audio_feedback', True):
                threading.Thread(target=AudioFeedback.play_start_beep, daemon=True).start()

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

        # Play stop beep if enabled
        if self.config.get_setting('audio_feedback', True):
            threading.Thread(target=AudioFeedback.play_stop_beep, daemon=True).start()

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

        if transcription and transcription.strip():
            cleaned = transcription.strip()
            blank_indicators = ["[blank_audio]", "(blank)", "(silence)", "[silence]", "[BLANK_AUDIO]"]
            is_blank = any(indicator.lower() in cleaned.lower() for indicator in blank_indicators)

            if not is_blank:
                # Show in text area for reference
                self.transcription_text.append(cleaned)

                # Inject text as a single batch operation (not character-by-character streaming)
                # This waits for full transcription then types it all at once
                # Future: LLM text editing step can be inserted here before injection
                success = self.text_injector.inject_text(cleaned)

                if success:
                    self._update_status("Text injected")
                else:
                    self._update_status("Copied to clipboard")
            else:
                self._update_status("No speech detected")
        else:
            self._update_status("No speech detected")

    def _reset_record_button(self):
        """Reset the record button to ready state"""
        self.record_btn.setText("⏺")
        self.record_btn.setToolTip("Start recording")
        self.record_btn.setObjectName("primary")
        self.record_btn.setEnabled(True)
        self.record_btn.setStyle(self.record_btn.style())
        self.pause_btn.setVisible(False)

    def _update_status(self, status: str):
        """Update status display"""
        self.status_label.setText(status)

        if "Recording" in status:
            self.status_label.setObjectName("status_recording")
        elif "Processing" in status:
            self.status_label.setObjectName("status_processing")
        elif "Paused" in status:
            self.status_label.setObjectName("status_paused")
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
            # Use stop symbol ⏹ when recording
            self.record_btn.setText("⏹")
            self.record_btn.setToolTip("Stop recording")
            self.record_btn.setObjectName("recording")
            self.pause_btn.setVisible(True)
            self._update_status("Recording...")
        elif self.is_processing:
            self.record_btn.setText("⏳")
            self.record_btn.setToolTip("Processing...")
            self.record_btn.setEnabled(False)
            self.pause_btn.setVisible(False)
            self._update_status("Processing...")
        else:
            # Use record symbol ⏺ when ready
            self.record_btn.setText("⏺")
            self.record_btn.setToolTip("Start recording")
            self.record_btn.setObjectName("primary")
            self.record_btn.setEnabled(True)
            self.pause_btn.setVisible(False)
            self.is_paused = False
            self._update_status("Ready")

        # Force style update
        self.record_btn.setStyle(self.record_btn.style())

        # Update tray icon based on recording state
        self._update_tray_icon(is_recording)

    def _update_pause_ui(self, is_paused: bool):
        """Update UI for pause state"""
        if is_paused:
            # Use play symbol ▶ to indicate "click to resume"
            self.pause_btn.setText("▶")
            self.pause_btn.setToolTip("Resume recording")
            self.pause_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 20px;
                    background-color: {COLORS['warning']};
                    color: {COLORS['background']};
                }}
                QPushButton:hover {{
                    background-color: #e5d09e;
                }}
            """)
            self._update_status("Paused")
        else:
            # Use pause symbol ⏸
            self.pause_btn.setText("⏸")
            self.pause_btn.setToolTip("Pause recording")
            self.pause_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 20px;
                    background-color: {COLORS['surface_light']};
                }}
                QPushButton:hover {{
                    background-color: {COLORS['border']};
                }}
            """)
            if self.is_recording:
                self._update_status("Recording...")

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
                                 self.whisper_manager, self._update_displays,
                                 self.audio_capture)
        dialog.exec()

    def _update_displays(self):
        """Update all display labels from config"""
        self.model_display.setText(self.config.get_setting('model', 'large-v3'))
        # Show toggle shortcut in main display
        shortcuts = self.config.get_all_shortcuts()
        toggle_key = shortcuts.get('toggle', 'F13')
        self.shortcut_display.setText(toggle_key)
        self.delay_display.setText(f"{self.config.get_setting('key_delay', 15)}ms")
        self.mic_display.setText(self._get_current_mic_name())

        # Update always on top
        if self.config.get_setting('always_on_top', True):
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts when app is focused"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_C:
                # Ctrl+C: Copy transcription to clipboard
                self._copy_transcription()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_S:
                # Ctrl+S: Start/Stop recording
                self._toggle_recording()
                event.accept()
                return
        super().keyPressEvent(event)

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
