"""流浪猫的小字条: 显示在欢迎语 (猫猫的傲娇教程) 下面, 每次显示欢迎语时随机抽一张.

字条文案在 i18n/<locale>.json 的 "cat_notes" 里:
    prefix:         字条开头, 如 "🐈流浪猫对你说："
    normal:         日常字条
    rare:           稀有字条 (礼物 / 感应 / 异常 / 发现)
    late_night:     深夜字条
    monday_morning: 周一早上的字条

抽取规则:
    5%  稀有字条
    深夜 (23 点 ~ 5 点) 或周一早上 (7 ~ 10 点) 有 70% 的概率出现对应的应景字条
    其余从日常字条里随机抽
"""
import random
from datetime import datetime


def random_note(notes, now=None):
    """从 notes (load_locale 返回的 cat_notes) 里抽一张带前缀的字条; 没有字条时返回 None"""
    if not notes:
        return None
    now = now or datetime.now()
    hour, weekday = now.hour, now.weekday()

    if random.random() < 0.05:
        text = random.choice(notes["rare"])
    elif random.random() < 0.7 and (hour >= 23 or hour <= 5):
        text = notes["late_night"]
    elif random.random() < 0.7 and weekday == 0 and 7 <= hour <= 10:
        text = notes["monday_morning"]
    else:
        text = random.choice(notes["normal"])
    return notes["prefix"] + text
