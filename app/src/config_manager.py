"""
Configuration manager for WhisperTux
Handles loading, saving, and managing application settings
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import shutil


class ConfigManager:
    """Manages application configuration and settings"""
    
    def __init__(self):
        # Resolve project paths early for defaults
        self.project_root = Path(__file__).resolve().parent.parent
        self.local_models_dir = self.project_root / "whisper.cpp" / "models"
        self.openai_whisper_dir = Path.home() / "ai" / "models" / "stt" / "openai-whisper" / "models"
        self.local_whisper_binary = self.project_root / "whisper.cpp" / "build" / "bin" / "whisper-cli"

        # Default configuration values
        self.default_config = {
            'primary_shortcut': 'F13',
            'model': 'large-v3',
            'custom_model_path': None,  # Direct path to a custom .bin model file
            'model_directories': [      # List of directories to scan for models
                str(self.local_models_dir),
                str(Path.home() / "ai" / "models" / "stt" / "whisper-cpp"),
                str(self.openai_whisper_dir),
                str(Path.home() / "ai" / "models" / "stt" / "finetunes"),
                str(Path.home() / "ai" / "models" / "stt" / "by-program" / "dsnote"),  # Contains large-v3-turbo
            ],
            'key_delay': 15,  # Delay between keystrokes in milliseconds for ydotool
            'use_clipboard': False,
            'window_position': None,
            'always_on_top': True,
            'theme': 'darkly',
            'audio_device': None,  # None means use system default
            'word_overrides': {},  # Dictionary of word replacements: {"original": "replacement"}
            'transcription_threads': max(1, os.cpu_count() // 2) if os.cpu_count() else 4,
            'whisper_binary': None,  # Optional override for whisper-cli path
        }
        
        # Set up config directory and file path
        self.config_dir = Path.home() / '.config' / 'whispertux'
        self.config_file = self.config_dir / 'config.json'
        
        # Current configuration (starts with defaults)
        self.config = self.default_config.copy()
        
        # Ensure config directory exists
        self._ensure_config_dir()
        
        # Load existing configuration
        self._load_config()
    
    def _ensure_config_dir(self):
        """Ensure the configuration directory exists"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            try:
                from .logger import log_warning
                log_warning(f"Could not create config directory: {e}", "CONFIG")
            except ImportError:
                print(f"Warning: Could not create config directory: {e}")
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    
                # Merge loaded config with defaults (preserving any new default keys)
                self.config.update(loaded_config)
                print(f"Configuration loaded from {self.config_file}")
            else:
                print("No existing configuration found, using defaults")
                # Save default configuration
                self.save_config()
                
        except Exception as e:
            print(f"Warning: Could not load configuration: {e}")
            print("Using default configuration")
    
    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"Error: Could not save configuration: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting"""
        return self.config.get(key, default)
    
    def set_setting(self, key: str, value: Any):
        """Set a configuration setting"""
        self.config[key] = value
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration settings"""
        return self.config.copy()
    
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.config = self.default_config.copy()
        print("Configuration reset to defaults")
    
    def update_shortcuts(self, primary: Optional[str] = None, secondary: Optional[str] = None):
        """Update shortcut configuration"""
        if primary is not None:
            self.config['primary_shortcut'] = primary
            
        return self.save_config()
    
    def get_whisper_model_path(self, model_name: str) -> Path:
        """Get the path to a whisper model file

        Supports:
        - Standard model names (tiny, base, small, medium, large)
        - Custom model paths (absolute paths to .bin files)
        - Scanning multiple model directories
        """
        # Check if custom_model_path is set and we're asking for the current model
        custom_path = self.config.get('custom_model_path')
        if custom_path and model_name == self.config.get('model'):
            custom_path = Path(custom_path)
            if custom_path.exists():
                return custom_path

        # If model_name is an absolute path, use it directly
        if model_name and (model_name.startswith('/') or model_name.startswith('~')):
            expanded_path = Path(model_name).expanduser()
            if expanded_path.exists():
                return expanded_path

        # Get model directories from config
        model_dirs = self.config.get('model_directories', [
            str(Path.home() / "ai" / "models" / "stt" / "whisper-cpp")
        ])

        # Search for the model in each directory
        for model_dir_str in model_dirs:
            model_dir = Path(model_dir_str).expanduser()
            if not model_dir.exists():
                continue

            # Handle different model naming conventions
            if model_name.endswith('.en'):
                # English-only model
                model_path = model_dir / f"ggml-{model_name}.bin"
                if model_path.exists():
                    return model_path
            else:
                # Check both .en.bin and .bin versions
                en_model_path = model_dir / f"ggml-{model_name}.en.bin"
                multi_model_path = model_dir / f"ggml-{model_name}.bin"

                if en_model_path.exists():
                    return en_model_path
                elif multi_model_path.exists():
                    return multi_model_path

            # Also check for generic ggml-model.bin (common for finetunes)
            generic_path = model_dir / "ggml-model.bin"
            if generic_path.exists() and model_name in str(model_dir):
                return generic_path

        # Default fallback: return expected path in first model directory
        default_dir = Path(model_dirs[0]).expanduser() if model_dirs else Path.home() / "ai" / "models" / "stt" / "whisper-cpp"
        return default_dir / f"ggml-{model_name}.en.bin"

    def get_model_directories(self) -> list:
        """Get list of model directories"""
        dirs = self.config.get('model_directories', [])

        # Ensure local whisper.cpp models directory is first if it exists
        if self.local_models_dir.exists():
            local_dir = str(self.local_models_dir)
            if local_dir not in dirs:
                dirs.insert(0, local_dir)

        # Always return at least the default whisper.cpp location
        if not dirs:
            dirs = [str(Path.home() / "ai" / "models" / "stt" / "whisper-cpp")]

        return dirs

    def add_model_directory(self, directory: str) -> bool:
        """Add a new directory to scan for models"""
        dirs = self.config.get('model_directories', [])
        expanded = str(Path(directory).expanduser())
        if expanded not in dirs:
            dirs.append(expanded)
            self.config['model_directories'] = dirs
            return True
        return False

    def remove_model_directory(self, directory: str) -> bool:
        """Remove a directory from model scanning"""
        dirs = self.config.get('model_directories', [])
        expanded = str(Path(directory).expanduser())
        if expanded in dirs:
            dirs.remove(expanded)
            self.config['model_directories'] = dirs
            return True
        return False

    def set_custom_model_path(self, path: Optional[str]) -> bool:
        """Set a custom model path (absolute path to .bin file)"""
        if path:
            expanded = Path(path).expanduser()
            if expanded.exists() and expanded.suffix == '.bin':
                self.config['custom_model_path'] = str(expanded)
                return True
            return False
        else:
            self.config['custom_model_path'] = None
            return True

    def get_custom_model_path(self) -> Optional[str]:
        """Get the current custom model path"""
        return self.config.get('custom_model_path')

    def get_whisper_binary_path(self) -> Path:
        """Get the path to the whisper binary"""
        # 1) Explicit override from config
        override_binary = self.config.get('whisper_binary')
        if override_binary and Path(override_binary).exists():
            return Path(override_binary)

        # 2) Local build inside the project (preferred for matching model dir)
        if self.local_whisper_binary.exists():
            return self.local_whisper_binary

        # 3) whisper-cli in PATH
        whisper_cli = shutil.which("whisper-cli")
        if whisper_cli:
            return Path(whisper_cli)

        # Fallback to common locations
        possible_paths = [
            Path.home() / ".local" / "bin" / "whisper-cli",
            Path("/usr/local/bin/whisper-cli"),
            Path("/usr/bin/whisper-cli"),
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # Return the most likely path even if it doesn't exist yet
        return possible_paths[0]
    
    def get_temp_directory(self) -> Path:
        """Get the temporary directory for audio files"""
        # Use XDG data directory for user-writable temp files
        data_home = os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))
        temp_dir = Path(data_home) / 'whispertux' / 'temp'
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    def get_word_overrides(self) -> Dict[str, str]:
        """Get the word overrides dictionary"""
        return self.config.get('word_overrides', {}).copy()
    
    def add_word_override(self, original: str, replacement: str):
        """Add or update a word override"""
        if 'word_overrides' not in self.config:
            self.config['word_overrides'] = {}
        self.config['word_overrides'][original.lower().strip()] = replacement.strip()
    
    def remove_word_override(self, original: str):
        """Remove a word override"""
        if 'word_overrides' in self.config:
            self.config['word_overrides'].pop(original.lower().strip(), None)
    
    def clear_word_overrides(self):
        """Clear all word overrides"""
        self.config['word_overrides'] = {}
