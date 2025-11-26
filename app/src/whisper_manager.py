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
    
    def get_available_models(self) -> list:
        """Get list of available whisper models from all configured directories"""
        available_models = []
        model_paths = {}  # Track paths for display

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
                        if model_file.name.endswith('.en.bin'):
                            model_name = f"{model}.en"
                        else:
                            model_name = model

                        if model_name not in available_models:
                            available_models.append(model_name)
                            model_paths[model_name] = str(model_file)
                        break

            # Special handling for large-v3-turbo with alternate naming conventions
            if 'large-v3-turbo' not in available_models:
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
                        available_models.append('large-v3-turbo')
                        model_paths['large-v3-turbo'] = str(turbo_file)
                        break

            # Recursively scan for ggml-model.bin files (finetunes)
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

        return available_models

    def _scan_for_finetunes(self, base_dir: Path, models_list: list, paths_dict: dict, max_depth: int = 5):
        """Recursively scan directory for finetune models (ggml-model.bin files)"""
        if max_depth <= 0:
            return

        try:
            for item in base_dir.iterdir():
                if item.is_dir():
                    # Check for ggml-model.bin in this directory
                    ggml_model = item / "ggml-model.bin"
                    if ggml_model.exists():
                        # Get the full path relative to base_dir for analysis
                        try:
                            rel_path = ggml_model.relative_to(base_dir)
                            path_parts = rel_path.parts[:-1]  # Exclude the filename
                        except ValueError:
                            path_parts = [item.name]

                        # Try to extract meaningful name from path
                        # Look for directories that contain 'finetune', 'acft', or model identifiers
                        finetune_name = None
                        is_finetune = 'finetune' in str(ggml_model).lower() or 'acft' in str(ggml_model).lower()

                        for part in path_parts:
                            part_lower = part.lower()
                            # Skip generic directory names
                            if part_lower in ['inference-formats', 'ggml-whisper-cpp', 'ggml', 'v2', 'models']:
                                continue
                            # Look for finetune identifier
                            if 'finetune' in part_lower or 'acft' in part_lower or 'whisper' in part_lower:
                                finetune_name = part
                                # Don't break - prefer later (more specific) matches

                        # Build display name
                        label = "[Finetune]" if is_finetune else "[Custom]"
                        if finetune_name:
                            display_name = f"{label} {finetune_name}"
                        else:
                            # Use the parent directory name as identifier
                            # Go up from ggml/ggml-whisper-cpp to find meaningful name
                            parent_chain = []
                            current = item.parent
                            for _ in range(4):
                                if current.name.lower() not in ['inference-formats', 'ggml-whisper-cpp', 'ggml']:
                                    parent_chain.insert(0, current.name)
                                current = current.parent
                                if current == base_dir:
                                    break
                            if parent_chain:
                                display_name = f"{label} {parent_chain[-1]}"
                            else:
                                display_name = f"{label} {item.parent.name}"

                        # Avoid duplicates by checking the path, not just the name
                        # If same name exists but different path, add suffix
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

        except PermissionError:
            pass  # Skip directories we can't read

    def get_model_path(self, model_name: str) -> Optional[Path]:
        """Get the full path for a model by name"""
        # Check cached paths first
        if hasattr(self, '_model_paths') and model_name in self._model_paths:
            return Path(self._model_paths[model_name])

        # Fall back to config manager
        return self.config.get_whisper_model_path(model_name)
