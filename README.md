# WhisperTux (Fork)

This is a fork of [WhisperTux](https://github.com/cjams/whispertux) - a simple voice dictation application for Linux.

## Fork Modifications

This fork includes the following changes from the original:

1. **Virtual environment setup with UV** - Added `setup-venv.sh` script that uses `uv` for faster venv creation and dependency installation

2. **Default keybinding changed to F13** - The default shortcut is now F13 instead of F12, useful for dedicated macro keys

3. **Reorganized directory structure** - Application code moved into `app/` folder for cleaner organization

4. **Debian packaging support** - Added build scripts to create `.deb` packages for easier installation

## Installation

### From Source

```bash
cd app
./setup-venv.sh
python3 setup.py
```

### From Debian Package

```bash
./build/build-deb.sh
sudo dpkg -i build/whispertux_*.deb
```

## Original Project

For full documentation, features, and troubleshooting, see the original project:
- **Repository**: https://github.com/cjams/whispertux
- **Original README**: [app/docs/](app/docs/)

## License

MIT License (see [LICENSE](LICENSE))
