# -*- coding: utf-8 -*-
"""
بوت الطالب الشامل (Telegram)
- قسم للطالب المدرسي وقسم للطالب الجامعي
- الحد اليومي: 3 عمليات (للأدوات الثقيلة)، الأدوات الحسابية مجانية
- التوكن يُقرأ من متغير البيئة BOT_TOKEN (لا تكتبه داخل الكود)
"""
import ast
import asyncio
import logging
import math
import operator
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ───────────────────────── الإعدادات ─────────────────────────