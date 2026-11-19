# LLM Translate(流浪猫翻译)

## 安装

```bash
uv venv venv --python=3.12
```
```bash
source venv/bin/activate
```
```bash
uv pip install -r requirements.txt
```


## 打包

macOS:
```bash
pyinstaller --name "流浪猫翻译" --clean --noconfirm --windowed --hidden-import=ttkbootstrap --icon=app.ico --add-data="app.png:." --add-data="config.json:." --add-data="i18n:i18n" main.py
```

Windows:
```bash
pyinstaller --name "流浪猫翻译" --clean --noconfirm --onefile --windowed --hidden-import=ttkbootstrap --icon=app.ico --add-data="app.png;." --add-data="config.json;." --add-data="i18n;i18n" main.py
```

