import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttkb
from ttkbootstrap.widgets import ToastNotification

import pyperclip

import os
import queue
import re
import sys
import threading
import traceback
import time

from prompt import translate_template
from llm import LLM
from config import APP_NAME, resource_path, has_user_config, load_config, save_config
from i18n import resolve_locale, load_locale, available_locales

# macOS 从 Finder 启动 .app 时没有 LANG, pyperclip 调用的 pbpaste 会按 GBK 等旧编码输出,
# 剪切板里有中文/日文时按 UTF-8 解码直接崩溃
if sys.platform == "darwin" and "UTF-8" not in os.environ.get("LANG", "").upper():
    os.environ["LANG"] = "en_US.UTF-8"

# 汉字 / 假名 / 谚文
CJK_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯豈-﫿]")


class TransApp:
    def __init__(self, root):
        # config: 有已保存的用户配置就直接开始翻译, 否则显示设置表单
        self.config = load_config()
        # 界面语言在启动时和切换语言时确定; 翻译的目标语言在每次翻译前重新确定 (见 translate)
        self.ui = load_locale(resolve_locale(self.config))["ui"]
        self.status_msg = None        # 标题栏 [...] 里的状态
        self.showing_welcome = False  # 文本框里是否还是欢迎语 (切换语言时要跟着换)

        # translate
        self.max_limit = 10000
        self.llm = None
        self.trans_container = None
        self.config_frame = None

        # init window
        self.root = root

        self.root.title(self.ui["app_name"])
        if self.root.tk.call("tk", "windowingsystem") == "aqua":
            # macOS 深色模式下标题栏是黑色, 和浅色的 minty 主题不搭, 固定用浅色外观
            self.root.tk.call("::tk::unsupported::MacWindowStyle", "appearance", self.root._w, "aqua")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.9)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.set_menu()

        self.last_content = pyperclip.paste()

        # init monitor
        self.monitoring = True
        self.monitor_thread = None

        # Tk 不是线程安全的: 监听线程直接调用 root.after 在打包后的应用里会让进程崩溃
        # (Fatal Python error: PyEval_RestoreThread). 后台线程只往队列里放更新, 由主线程执行
        self.ui_queue = queue.Queue()
        self.process_ui_queue()

        if has_user_config():
            self.start_translating()
        else:
            self.set_config_inp_ui()

    def start_translating(self):
        """根据 self.config 创建 LLM, 显示翻译界面, 启动剪切板监听 (修改设置后也会再次调用)"""
        self.llm = LLM(**self.config["llm"])
        if self.trans_container is None:
            self.set_trans_ui()
        else:
            self.trans_container.pack(fill="both", expand=True)
        if self.monitor_thread is None:
            self.start_monitor_thread()

    def set_menu(self):
        """菜单栏: macOS 显示在屏幕顶部的系统菜单栏, Windows 显示在窗口标题下方"""
        menubar = tk.Menu(self.root)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label=self.ui["menu_llm_config"], command=self.open_settings)

        # 语言: 同时决定界面文字和翻译的目标语言; "" 表示自动 (按 IP 所在地区)
        self.locale_var = tk.StringVar(self.root, value=self.config.get("locale") or "")
        language_menu = tk.Menu(settings_menu, tearoff=0)
        language_menu.add_radiobutton(label=self.ui["language_auto"], value="",
                                      variable=self.locale_var, command=self.on_language_selected)
        language_menu.add_separator()
        for locale, name in available_locales():
            language_menu.add_radiobutton(label=name, value=locale,
                                          variable=self.locale_var, command=self.on_language_selected)
        settings_menu.add_cascade(label=self.ui["menu_language"], menu=language_menu)

        menubar.add_cascade(label=self.ui["menu_settings"], menu=settings_menu)
        self.root.config(menu=menubar)
        # macOS: 让应用菜单里的 "偏好设置…" (Cmd+,) 也打开配置
        if self.root.tk.call("tk", "windowingsystem") == "aqua":
            self.root.createcommand("tk::mac::ShowPreferences", self.open_settings)

    def on_language_selected(self):
        locale = self.locale_var.get()
        if locale == (self.config.get("locale") or ""):
            return
        if locale:
            self.config["locale"] = locale
        else:
            self.config.pop("locale", None)
        save_config(self.config)
        self.ui = load_locale(resolve_locale(self.config))["ui"]
        self.apply_ui_language()
        # 已经有翻译结果时, 把当前剪切板内容按新的目标语言重新翻译一次
        if self.trans_container is not None and not self.showing_welcome:
            self.last_content = None

    def apply_ui_language(self):
        """切换语言后刷新所有界面文字"""
        self.set_menu()
        if self.showing_welcome:
            self.show_welcome()
        else:
            self.update_status(self.status_msg)
        if self.config_frame is not None:
            for widget, key in self.config_widgets:
                widget.config(text=self.ui[key])

    def open_settings(self):
        if self.config_frame is not None:  # 配置表单已经打开
            return
        if self.trans_container is not None:
            self.trans_container.pack_forget()
        self.set_config_inp_ui()

    def set_config_inp_ui(self):
        llm_conf = self.config["llm"]
        base_url, api_key, model = llm_conf["base_url"], llm_conf["api_key"], llm_conf["model"]

        frame = ttk.Frame(self.root, padding="10")
        frame.pack(fill="x", padx=10, pady=10)
        self.config_frame = frame

        # Base URL
        base_url_label = ttk.Label(frame, text=self.ui["base_url"])
        base_url_label.grid(row=0, column=0, sticky="w", pady=5)
        base_url_entry = ttk.Entry(frame, width=30)
        base_url_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        base_url_entry.insert(0, base_url)

        # Api Key
        api_key_label = ttk.Label(frame, text=self.ui["api_key"])
        api_key_label.grid(row=1, column=0, sticky="w", pady=5)
        api_key_entry = ttk.Entry(frame, width=30)
        api_key_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        api_key_entry.insert(0, api_key)

        # Model
        model_label = ttk.Label(frame, text=self.ui["model"])
        model_label.grid(row=2, column=0, sticky="w", pady=5)
        model_entry = ttk.Entry(frame, width=30)
        model_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        model_entry.insert(0, model)

        # button
        def on_click():
            self.config["llm"] = {
                "base_url": base_url_entry.get().strip(),
                "api_key": api_key_entry.get().strip(),
                "model": model_entry.get().strip(),
            }
            save_config(self.config)
            frame.destroy()
            self.config_frame = None
            self.start_translating()
        btn = ttkb.Button(frame, text=self.ui["ok"], command=on_click, bootstyle="success-outline")
        btn.grid(row=3, column=0, columnspan=2, pady=10)
        self.config_widgets = [(base_url_label, "base_url"), (api_key_label, "api_key"),
                               (model_label, "model"), (btn, "ok")]
        frame.columnconfigure(1, weight=1)

    def set_trans_ui(self):
        # init widgit
        self.trans_container = ttk.Frame(self.root)
        self.trans_container.pack(fill="both", expand=True)

        self.text_frame = ttk.Frame(self.trans_container)
        self.text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.clipboard_text = tk.Text(
            self.text_frame,
            wrap="word",
            font=("微软雅黑", 13),
            state="normal"
        )
        self.clipboard_text.pack(side="left", fill="both", expand=True)
        self.scrollbar = ttk.Scrollbar(self.text_frame, command=self.clipboard_text.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.clipboard_text.config(yscrollcommand=self.scrollbar.set)
    
        # init info
        self.root.after(0, self.show_welcome)

    def show_welcome(self):
        self.update_text(self.ui["welcome"])
        self.update_status(self.ui["welcome_status"])
        self.showing_welcome = True

    def post(self, func, *args):
        """从后台线程安排一次界面更新 (线程安全)"""
        self.ui_queue.put((func, args))

    def process_ui_queue(self):
        """主线程: 执行队列里的界面更新, 每 30ms 检查一次"""
        while True:
            try:
                func, args = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            func(*args)
        self.root.after(30, self.process_ui_queue)

    def start_monitor_thread(self):
        self.monitor_thread = threading.Thread(
            target=self.monitor_clipboard,
            daemon=True
        )
        self.monitor_thread.start()

    def monitor_clipboard(self):
        while self.monitoring:
            try:
                current = pyperclip.paste()
                if current != self.last_content and current.strip():
                    self.last_content = current
                    if len(current) > self.max_limit:
                        self.post(self.clear_text)
                        self.post(self.update_text, self.ui["too_long"])
                        continue
                    self.post(self.clear_text)
                    start_time = time.time()
                    predict_time = self.predict(current)
                    def print_func_factory():
                        def print_func(chunk):
                            self.post(self.update_text_stream, chunk)
                            now = time.time()
                            self.post(self.update_status, self.progress_bar((now-start_time)/predict_time))
                        return print_func
                    translate_content, token_usage = self.translate(current, print_func=print_func_factory())
                    end_time = time.time()
                    # time_cost = end_time-start_time
                    self.post(self.update_status, f"{self.progress_bar(1)} token: {token_usage}")
                    self.post(self.update_text, translate_content)
                time.sleep(0.3)
                
            except Exception as e:
                print(f"剪切板监听错误: {e}")
                traceback.print_exc()
                time.sleep(2)
    
    def update_status(self, msg):
        self.status_msg = msg
        title = self.ui["app_name"]
        self.root.title(f"{title}[{msg}]" if msg is not None else title)

    def update_text(self, text):
        self.clipboard_text.config(state="normal")
        self.clipboard_text.delete("1.0", "end")
        self.clipboard_text.insert("1.0", text)
        self.clipboard_text.config(state="disabled")

    def update_text_stream(self, chunk):
        self.clipboard_text.insert("end", chunk)
    
    def clear_text(self):
        self.showing_welcome = False
        self.clipboard_text.config(state="normal")
        self.clipboard_text.delete("1.0", "end")

    def toast_msg(self, msg):
        toast = ToastNotification(
            title=self.ui["app_name"],
            message=msg,
            duration=5000,
            icon="😺"
        )
        toast.show_toast()

    def run(self):
        self.root.mainloop()

    def on_closing(self):
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        self.root.destroy()
        print("over")

    def translate(self, text, print_func=None):
        target_lang = load_locale(resolve_locale(self.config))["target_lang"]
        prompt = translate_template.substitute(target_lang=target_lang, text=text)
        res, tk = self.llm(prompt, print_func=print_func)
        return res, tk
    
    @staticmethod
    def predict(text):
        """预估翻译耗时 (秒), 用于进度条.

        2026-11-19 对 Index-Translate-35B-A3B 实测 (英/日 10~2500 字, 各 3 次) 按相对误差拟合:
        耗时主要取决于输出长度, 中日韩文字翻译后几乎等长, 英文等翻成中文后约缩短到 1/3,
        所以两类字符分开计; 长文本生成会变慢, 加一个平方项.
        """
        n = len(text)
        cjk = len(CJK_RE.findall(text))
        return 1.059 + 0.017157 * cjk + 0.004077 * (n - cjk) + 3.63e-6 * n * n
    
    @staticmethod
    def progress_bar(progress):
        if progress >= 1:
            return "😺"
        percentage = int(progress * 100)
        percentage = max(0, min(percentage, 100))
        dots_1 = int((100-percentage) // 10)
        dots_2 = 8 - dots_1
        bar = "🐟" + "."*dots_1 + "🐈" + "."*dots_2
        return f"{bar}: {percentage:2d}%"

if __name__ == "__main__":

    root = ttkb.Window(
            title=APP_NAME,
            themename="minty",
            size=(300, 300),
            iconphoto=resource_path("app.png")
    )
    app = TransApp(root=root)
    app.run()
