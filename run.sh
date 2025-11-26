#!/usr/bin/env bash
# Wrapper to start WhisperTux with the bundled ROCm/HIP whisper.cpp binary + libs
# Vulkan bundle (default)
BASE="${HOME}/programs/speech-voice/libraries/whispercpp-vulkan"

VENV="${HOME}/programs/speech-voice/apps/forks/whispertux/.venv-sys"
PYBIN="${VENV}/bin/python"

export LD_LIBRARY_PATH="${BASE}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"

# If you want the CLI directly, call with --cli ...
if [[ "$1" == "--cli" ]]; then
  shift
  exec "${BASE}/whisper-cli" "$@"
fi

# Otherwise launch the GUI app with the Tk-enabled venv
exec "${PYBIN}" app/main.py
