"""本地化: 决定使用哪种语言, 并读取 i18n/<locale>.json.

语言的决定顺序:
    1. config.json 里的 "locale" (如 "zh_CN"), 手动指定时不再查询 IP
    2. ip-api 查询当前 IP 所在国家/地区, 按 i18n/countries.json 对应到 locale
    3. 以上都没有结果时用 DEFAULT_LOCALE

每个 i18n/<locale>.json 包含:
    language_name: 该语言自己的名称, 显示在 "语言" 菜单里
    target_lang: 翻译的目标语言 (填进中文 prompt, 所以写中文名称)
    ui:          界面文字, 缺少的键用 en.json 补齐
    cat_notes:   欢迎语下面的流浪猫小字条 (格式见 cat_notes.py), 缺少时用 en.json 的
"""
import os
import time
from functools import lru_cache

import requests

from config import resource_path, read_json

I18N_DIR = resource_path("i18n")
DEFAULT_LOCALE = "zh_CN"
BASE_LOCALE = "en"

# ip-api 免费版只支持 http, 限制 45 次/分钟
IP_API_URL = "http://ip-api.com/json/?fields=status,countryCode"
IP_API_TIMEOUT = 2          # 秒
IP_API_CACHE_SECONDS = 6000  # 100 分钟内复用上一次的结果

_ip_cache = {"locale": None, "time": 0.0}


@lru_cache(maxsize=None)
def _country_locales():
    """{"JP": "ja", ...}, 由 countries.json 的 {locale: [国家代码, ...]} 反转而来"""
    table = read_json(os.path.join(I18N_DIR, "countries.json"))
    return {country: locale for locale, countries in table.items() for country in countries}


def detect_locale():
    """根据 IP 所在国家/地区返回 locale; 失败时返回上一次的结果 (可能为 None)"""
    now = time.time()
    if _ip_cache["locale"] and now - _ip_cache["time"] < IP_API_CACHE_SECONDS:
        return _ip_cache["locale"]
    try:
        r = requests.get(IP_API_URL, timeout=IP_API_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "success":
            locale = _country_locales().get(data.get("countryCode"), DEFAULT_LOCALE)
            _ip_cache.update(locale=locale, time=now)
    except (requests.RequestException, ValueError):
        pass
    return _ip_cache["locale"]


@lru_cache(maxsize=None)
def available_locales():
    """[(locale, 语言名称), ...], 顺序同 countries.json, 其余按文件名排在后面"""
    files = sorted(f[:-5] for f in os.listdir(I18N_DIR)
                   if f.endswith(".json") and f != "countries.json")
    order = list(read_json(os.path.join(I18N_DIR, "countries.json")))
    files.sort(key=lambda loc: order.index(loc) if loc in order else len(order))
    return [(loc, load_locale(loc)["language_name"]) for loc in files]


def resolve_locale(conf):
    return conf.get("locale") or detect_locale() or DEFAULT_LOCALE


@lru_cache(maxsize=None)
def load_locale(locale):
    """读取 locale 文件, ui 缺少的键和 cat_notes 用英文补齐; 文件不存在时用 DEFAULT_LOCALE"""
    path = os.path.join(I18N_DIR, f"{locale}.json")
    if not os.path.exists(path):
        path = os.path.join(I18N_DIR, f"{DEFAULT_LOCALE}.json")
    data = read_json(path)
    ui = {**read_json(os.path.join(I18N_DIR, f"{BASE_LOCALE}.json"))["ui"], **data.get("ui", {})}
    cat_notes = data.get("cat_notes") or read_json(os.path.join(I18N_DIR, f"{BASE_LOCALE}.json")).get("cat_notes")
    return {"language_name": data.get("language_name", locale),
            "target_lang": data["target_lang"], "ui": ui, "cat_notes": cat_notes}
