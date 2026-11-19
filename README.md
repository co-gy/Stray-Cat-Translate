# Stray Cat Translate (流浪猫翻译)

A minimal translator. Copy any text and it gets translated by an LLM.


https://github.com/user-attachments/assets/4634c2e7-42ca-4cf5-907a-336d52fa0a03



## Download

[Releases](https://github.com/co-gy/Stray-Cat-Translate/releases) (macOS, Apple Silicon)

## Usage

1. On first launch, confirm the LLM settings. They default to the free API of Bilibili's [Index-Translate](https://github.com/bilibili/Index-Translate); any OpenAI-compatible API works.
2. Copy text anywhere, and the translation appears in the window.

Change settings anytime via **Settings → LLM Settings…** in the menu bar.

Pick the language under **Settings → Language**. It sets both the interface language and the language text is translated into. **Auto** chooses it from your location.

## Build from source

```bash
uv venv venv --python=3.12
source venv/bin/activate
uv pip install -r requirements.txt
```

macOS:
```bash
pyinstaller --name "流浪猫翻译" --clean --noconfirm --windowed --hidden-import=ttkbootstrap --icon=app.ico --add-data="app.png:." --add-data="config.json:." --add-data="i18n:i18n" main.py
```

Windows:
```bash
pyinstaller --name "流浪猫翻译" --clean --noconfirm --onefile --windowed --hidden-import=ttkbootstrap --icon=app.ico --add-data="app.png;." --add-data="config.json;." --add-data="i18n;i18n" main.py
```
