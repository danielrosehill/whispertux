"""
Text injector for WhisperTux
Handles injecting transcribed text into other applications using ydotool
"""

import subprocess
import time
import pyperclip
from typing import Optional


class TextInjector:
    """Handles injecting text into focused applications"""

    def __init__(self, config_manager=None):
        # Configuration
        self.config_manager = config_manager

        # Initialize settings from config if available
        if self.config_manager:
            self.key_delay = self.config_manager.get_setting('key_delay', 15)
        else:
            self.key_delay = 15  # Default key delay in milliseconds

        # Check if ydotool is available
        self.ydotool_available = self._check_ydotool()

        if not self.ydotool_available:
            print("ydotool not found - text injection will use clipboard fallback")

    def _check_ydotool(self) -> bool:
        """Check if ydotool is available on the atiystem"""
        try:
            result = subprocess.run(['which', 'ydotool'],
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0


        except:
            return False

    def inject_text(self, text: str) -> bool:
        """
        Inject text into the currently focused application.

        Always copies to clipboard first as a backup, then attempts ydotool
        injection for direct text entry. If ydotool fails or no focused text
        field exists, the text is still available via Ctrl+V.

        Args:
            text: Text to inject

        Returns:
            True if successful, False otherwise
        """
        if not text or text.strip() == "":
            print("No text to inject (empty or whitespace)")
            return True

        # Preprocess the text to handle unwanted carriage returns and speech-to-text corrections
        processed_text = self._preprocess_text(text)

        try:
            # Always copy to clipboard first as a backup
            # This ensures text is never lost even if ydotool injection fails
            # (e.g., no focused text field, cursor not in an input, etc.)
            self._copy_to_clipboard(processed_text)

            # Then try ydotool for direct text entry if available
            if self.ydotool_available:
                success = self._inject_via_ydotool(processed_text)
                if not success:
                    print("ydotool injection failed - text is available in clipboard (Ctrl+V)")
                return success
            else:
                # ydotool not available - clipboard is the only option
                print("Text copied to clipboard - paste with Ctrl+V")
                return True

        except Exception as e:
            print(f"Text injection failed: {e} - text may still be in clipboard")
            return False

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text to handle common speech-to-text corrections and remove unwanted line breaks
        """
        import re
        
        # First, convert unwanted carriage returns and newlines to spaces
        # This prevents accidental "Enter" key presses in applications
        processed = text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
        
        # Apply user-defined word overrides first (before built-in corrections)
        processed = self._apply_word_overrides(processed)
        
        # Handle common speech-to-text corrections
        replacements = {
            r'\bperiod\b': '.',
            r'\bcomma\b': ',',
            r'\bquestion mark\b': '?',
            r'\bexclamation mark\b': '!',
            r'\bcolon\b': ':',
            r'\bsemicolon\b': ';',
            r'\btux enter\b': '\n',     # Special phrase for new line
            r'\btab\b': '\t',
            r'\bdash\b': '-',
            r'\bunderscore\b': '_',
            r'\bopen paren\b': '(',
            r'\bclose paren\b': ')',
            r'\bopen bracket\b': '[',
            r'\bclose bracket\b': ']',
            r'\bopen brace\b': '{',
            r'\bclose brace\b': '}',
            r'\bat symbol\b': '@',
            r'\bhash\b': '#',
            r'\bdollar sign\b': '$',
            r'\bpercent\b': '%',
            r'\bcaret\b': '^',
            r'\bampersand\b': '&',
            r'\basterisk\b': '*',
            r'\bplus\b': '+',
            r'\bequals\b': '=',
            r'\bless than\b': '<',
            r'\bgreater than\b': '>',
            r'\bslash\b': '/',
            r'\bbackslash\b': r'\\',
            r'\bpipe\b': '|',
            r'\btilde\b': '~',
            r'\bgrave\b': '`',
            r'\bquote\b': '"',
            r'\bapostrophe\b': "'",
        }

        for pattern, replacement in replacements.items():
            processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)

        # Clean up extra spaces but preserve intentional newlines
        processed = re.sub(r'[ \t]+', ' ', processed)  # Multiple spaces/tabs to single space
        processed = re.sub(r' *\n *', '\n', processed)  # Clean spaces around newlines
        processed = processed.strip()

        return processed
    
    def _apply_word_overrides(self, text: str) -> str:
        """
        Apply user-defined word overrides to the text
        """
        import re
        
        if not self.config_manager:
            return text
        
        # Get word overrides from configuration
        word_overrides = self.config_manager.get_word_overrides()
        
        if not word_overrides:
            return text
        
        processed = text
        
        # Apply each override using word boundary matching for accuracy
        for original, replacement in word_overrides.items():
            if original and replacement:
                # Use word boundaries to match whole words only
                # This prevents partial word replacements
                pattern = r'\b' + re.escape(original) + r'\b'
                processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)
        
        return processed

    def _copy_to_clipboard(self, text: str) -> bool:
        """Copy text to clipboard as a backup/fallback"""
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            print(f"Warning: Failed to copy to clipboard: {e}")
            return False

    def _inject_via_ydotool(self, text: str) -> bool:
        """Inject text using ydotool with configurable --key-delay and raw text (no escaping)"""
        try:
            cmd = ['ydotool', 'type', '--key-delay', str(self.key_delay), text]
            
            print(f"Injecting text with ydotool: ydotool type --key-delay {self.key_delay} [text]")

            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return True
            else:
                print(f"ERROR: ydotool failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("ERROR: ydotool command timed out")
            return False
        except Exception as e:
            print(f"ERROR: ydotool injection failed: {e}")
            return False

    def _inject_via_clipboard(self, text: str) -> bool:
        """Inject text using clipboard + paste key combination"""
        try:
            # Save current clipboard content
            try:
                original_clipboard = pyperclip.paste()
            except:
                original_clipboard = ""

            # Set new clipboard content
            pyperclip.copy(text)

            # Small delay to ensure clipboard is set
            time.sleep(0.1)

            # Paste using ydotool Ctrl+V (if ydotool is available)
            if self.ydotool_available:
                # Use ydotool to send Ctrl+V
                result = subprocess.run(
                    ['ydotool', 'key', '29:1', '47:1', '47:0', '29:0'],
                    capture_output=True,
                    timeout=5
                )

                if result.returncode != 0:
                    print(f"  ydotool paste command failed: {result.stderr}")
            else:
                print("No method available to send paste command")
                print("   Text has been copied to clipboard - paste manually with Ctrl+V")

            # Restore original clipboard after a delay
            def restore_clipboard():
                time.sleep(2.0)  # Wait 2 seconds before restoring
                try:
                    pyperclip.copy(original_clipboard)
                except:
                    pass  # Ignore restore errors

            # Run restore in a separate thread so it doesn't block
            import threading
            restore_thread = threading.Thread(target=restore_clipboard, daemon=True)
            restore_thread.start()

            print("Text copied to clipboard and paste command sent")
            return True

        except Exception as e:
            print(f"ERROR: Clipboard injection failed: {e}")
            return False

    def get_status(self) -> dict:
        """Get the status of the text injector"""
        return {
            'ydotool_available': self.ydotool_available,
            'key_delay': self.key_delay
        }
