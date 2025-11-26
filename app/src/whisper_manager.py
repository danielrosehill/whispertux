"""
Whisper manager for WhisperTux
Handles interaction with whisper.cpp for audio transcription
"""

import subprocess
import tempfile
import os
import wave
import numpy as np
from pathlib import Path
from typing import Optional
try:
    from .config_manager import ConfigManager
except ImportError:
    from config_manager import ConfigManager


class WhisperManager:
    """Manages whisper.cpp integration for audio transcription"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        if config_manager is None:
            self.config = ConfigManager()
        else:
            self.config = config_manager
            
        # Whisper configuration
        self.current_model = self.config.get_setting('model', 'base')
        self.whisper_binary = None
        self.model_path = None
        self.temp_dir = None
        
        # Whisper process state
        self.current_process = None
        self.ready = False
        
    def initialize(self) -> bool:
        """Initialize the whisper manager and check dependencies"""
        try:
            # Get paths from config manager
            self.whisper_binary = self.config.get_whisper_binary_path()
            self.temp_dir = self.config.get_temp_directory()

            # Check if whisper binary exists
            if not self.whisper_binary.exists():
                print(f"ERROR: Whisper binary not found at: {self.whisper_binary}")
                print("  Please build whisper.cpp first by running the build scripts")
                return False

            # Scan for available models to populate the cache
            self.get_available_models()

            # Set model path based on current model - check cached paths first
            self.model_path = self.get_model_path(self.current_model)

            if self.model_path is None or not self.model_path.exists():
                # Try config manager as fallback
                self.model_path = self.config.get_whisper_model_path(self.current_model)

            # Check if model exists
            if not self.model_path.exists():
                print(f"ERROR: Whisper model not found at: {self.model_path}")
                print(f"  Please download the {self.current_model} model first")
                return False

            print(f"Whisper binary found: {self.whisper_binary}")
            print(f"Using model: {self.current_model} at {self.model_path}")

            self.ready = True
            return True

        except Exception as e:
            print(f"ERROR: Failed to initialize Whisper manager: {e}")
            return False
    
    def is_ready(self) -> bool:
        """Check if whisper is ready for transcription"""
        return self.ready
    
    def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio data using whisper.cpp
        
        Args:
            audio_data: NumPy array of audio samples (float32)
            sample_rate: Sample rate of the audio data
            
        Returns:
            Transcribed text string
        """
        if not self.ready:
            raise RuntimeError("Whisper manager not initialized")
        
        # Check if we have valid audio data
        if audio_data is None:
            print("No audio data provided to transcribe")
            return ""
        
        if len(audio_data) == 0:
            print("Empty audio data provided to transcribe")
            return ""
        
        # Check if audio is too short (less than 0.1 seconds)
        min_samples = int(sample_rate * 0.1)  # 0.1 seconds minimum
        if len(audio_data) < min_samples:
            print(f"Audio too short: {len(audio_data)} samples (minimum {min_samples})")
            return ""
        
        # Create temporary WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False, dir=self.temp_dir) as temp_file:
            temp_wav_path = temp_file.name
            
        try:
            # Save audio data as WAV file
            self._save_audio_as_wav(audio_data, temp_wav_path, sample_rate)
            
            # Run whisper.cpp transcription
            transcription = self._run_whisper(temp_wav_path)
            
            return transcription.strip() if transcription else ""
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_wav_path)
            except:
                pass  # Ignore cleanup errors
    
    def _save_audio_as_wav(self, audio_data: np.ndarray, filepath: str, sample_rate: int):
        """Save numpy audio data as a WAV file"""
        # Convert float32 to int16 for WAV format
        if audio_data.dtype == np.float32:
            # Scale from [-1, 1] to [-32768, 32767]
            audio_int16 = (audio_data * 32767).astype(np.int16)
        else:
            audio_int16 = audio_data.astype(np.int16)
        
        with wave.open(filepath, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
    
    def _run_whisper(self, audio_file_path: str) -> str:
        """Run whisper.cpp on the given audio file"""
        try:
            threads = self.config.get_setting('transcription_threads', 4)
            # Construct whisper.cpp command
            cmd = [
                str(self.whisper_binary),
                '-m', str(self.model_path),
                '-f', audio_file_path,
                '--output-txt',
                '--no-timestamps',
                '--language', 'en',
                '--threads', str(threads)
            ]
            
            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            if result.returncode == 0:
                # Try to read the output txt file
                txt_file = audio_file_path + '.txt'
                if os.path.exists(txt_file):
                    with open(txt_file, 'r') as f:
                        transcription = f.read().strip()
                    # Clean up the txt file
                    os.unlink(txt_file)
                    return transcription
                else:
                    # Fall back to stdout if no txt file
                    return result.stdout.strip()
            else:
                print(f"Whisper command failed with return code {result.returncode}")
                print(f"stderr: {result.stderr}")
                return ""
                
        except subprocess.TimeoutExpired:
            print("Whisper transcription timed out")
            return ""
        except Exception as e:
            print(f"Error running whisper: {e}")
            return ""
    
    def set_model(self, model_name: str) -> bool:
        """
        Change the whisper model

        Args:
            model_name: Name of the model (e.g., 'base', 'small', '[Finetune] finetune_base')

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if the new model exists using cached paths first
            new_model_path = self.get_model_path(model_name)

            if new_model_path is None or not new_model_path.exists():
                # Try config manager as fallback
                new_model_path = self.config.get_whisper_model_path(model_name)

            if not new_model_path.exists():
                print(f"ERROR: Model {model_name} not found at {new_model_path}")
                return False

            # Update current model
            self.current_model = model_name
            self.model_path = new_model_path

            # Update config - store model name and custom path if it's a finetune/custom
            self.config.set_setting('model', model_name)

            # If it's a finetune or custom model, also store the full path
            if model_name.startswith('[Finetune]') or model_name.startswith('[Custom]'):
                self.config.set_custom_model_path(str(new_model_path))
            else:
                self.config.set_custom_model_path(None)

            print(f"Switched to model: {model_name} at {new_model_path}")
            return True

        except Exception as e:
            print(f"ERROR: Failed to set model {model_name}: {e}")
            return False
    
    def get_current_model(self) -> str:
        """Get the current model name"""
        return self.current_model
    
    def _get_display_name(self, internal_name: str) -> str:
        """Convert internal model name to user-friendly display name"""
        # Standard stock models - remove .en suffix and add "stock"
        stock_models = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3', 'large-v3-turbo']

        # Check if it's a stock model (with or without .en suffix)
        base_name = internal_name.replace('.en', '')
        if base_name in stock_models:
            return f"{base_name} stock"

        # Finetune models - convert "[Finetune] name" to "name - fine tune"
        if internal_name.startswith('[Finetune] '):
            finetune_name = internal_name[11:]  # Remove "[Finetune] " prefix
            return f"{finetune_name} - fine tune"

        # Custom models - keep as is
        return internal_name

    def _get_internal_name(self, display_name: str) -> str:
        """Convert display name back to internal model name"""
        # Stock models - remove "stock" suffix
        if display_name.endswith(' stock'):
            return display_name[:-6]  # Remove " stock"

        # Finetune models - convert "name - fine tune" to "[Finetune] name"
        if display_name.endswith(' - fine tune'):
            finetune_name = display_name[:-12]  # Remove " - fine tune"
            return f"[Finetune] {finetune_name}"

        return display_name

    def get_available_models(self) -> list:
        """Get list of available whisper models from all configured directories"""
        available_models = []
        model_paths = {}  # Track paths for display
        internal_to_display = {}  # Map internal names to display names

        # Get all model directories from config
        model_dirs = self.config.get_model_directories()

        # Standard model names to look for
        supported_models = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3', 'large-v3-turbo']

        for model_dir_str in model_dirs:
            model_dir = Path(model_dir_str).expanduser()
            if not model_dir.exists():
                continue

            # Check for standard model files in this directory
            for model in supported_models:
                model_files = [
                    model_dir / f"ggml-{model}.en.bin",  # English-only
                    model_dir / f"ggml-{model}.bin"      # Multilingual
                ]

                for model_file in model_files:
                    if model_file.exists():
                        # Internal name for storage (e.g., "tiny" or "tiny.en")
                        if model_file.name.endswith('.en.bin'):
                            internal_name = f"{model}.en"
                        else:
                            internal_name = model

                        # Display name for UI (e.g., "tiny stock")
                        display_name = f"{model} stock"

                        if display_name not in available_models:
                            available_models.append(display_name)
                            model_paths[display_name] = str(model_file)
                            internal_to_display[internal_name] = display_name
                        break

            # Special handling for large-v3-turbo with alternate naming conventions
            turbo_display = 'large-v3-turbo stock'
            if turbo_display not in available_models:
                turbo_patterns = [
                    # Standard naming
                    model_dir / "ggml-large-v3-turbo.bin",
                    model_dir / "ggml-large-v3-turbo.en.bin",
                    # Alternate naming (used by dsnote, etc.)
                    model_dir / "multilang_whisper_large3_turbo.ggml",
                    model_dir / "whisper_large3_turbo.ggml",
                    model_dir / "large-v3-turbo.ggml",
                    model_dir / "ggml-large-v3-turbo.ggml",
                ]
                for turbo_file in turbo_patterns:
                    if turbo_file.exists():
                        available_models.append(turbo_display)
                        model_paths[turbo_display] = str(turbo_file)
                        internal_to_display['large-v3-turbo'] = turbo_display
                        break

            # Scan for finetune models in this directory
            self._scan_for_finetunes(model_dir, available_models, model_paths)

        # Add custom model path if set
        custom_path = self.config.get_custom_model_path()
        if custom_path and Path(custom_path).exists():
            custom_name = f"[Custom] {Path(custom_path).stem}"
            if custom_name not in available_models:
                available_models.append(custom_name)
                model_paths[custom_name] = custom_path

        # Store model paths for reference
        self._model_paths = model_paths
        self._internal_to_display = internal_to_display

        return available_models

    def _scan_for_finetunes(self, base_dir: Path, models_list: list, paths_dict: dict, max_depth: int = 3):
        """Scan directory for finetune models (.bin files)"""
        if max_depth <= 0:
            return

        try:
            for item in base_dir.iterdir():
                if item.is_dir():
                    # Check for ggml-model.bin in this directory (common finetune convention)
                    ggml_model = item / "ggml-model.bin"
                    if ggml_model.exists():
                        # Use directory name as finetune name
                        display_name = f"[Finetune] {item.name}"

                        # Avoid duplicates
                        base_display_name = display_name
                        counter = 1
                        while display_name in paths_dict and paths_dict[display_name] != str(ggml_model):
                            display_name = f"{base_display_name} ({counter})"
                            counter += 1

                        if display_name not in models_list:
                            models_list.append(display_name)
                            paths_dict[display_name] = str(ggml_model)

                    # Recurse into subdirectories
                    self._scan_for_finetunes(item, models_list, paths_dict, max_depth - 1)

                elif item.is_file() and item.suffix == '.bin':
                    # Check for standalone .bin files that look like finetunes
                    # Skip standard model files (they're already handled above)
                    stem_lower = item.stem.lower()
                    standard_patterns = ['ggml-tiny', 'ggml-base', 'ggml-small', 'ggml-medium', 'ggml-large']
                    is_standard = any(stem_lower.startswith(p) for p in standard_patterns)

                    if not is_standard and 'ggml' in stem_lower:
                        # This looks like a custom/finetune model
                        display_name = f"[Finetune] {item.stem}"

                        # Avoid duplicates
                        base_display_name = display_name
                        counter = 1
                        while display_name in paths_dict and paths_dict[display_name] != str(item):
                            display_name = f"{base_display_name} ({counter})"
                            counter += 1

                        if display_name not in models_list:
                            models_list.append(display_name)
                            paths_dict[display_name] = str(item)

        except PermissionError:
            pass  # Skip directories we can't read

    def get_model_path(self, model_name: str) -> Optional[Path]:
        """Get the full path for a model by name"""
        # Check cached paths first
        if hasattr(self, '_model_paths') and model_name in self._model_paths:
            return Path(self._model_paths[model_name])

        # Fall back to config manager
        return self.config.get_whisper_model_path(model_name)
