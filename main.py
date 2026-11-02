# -*- coding: utf-8 -*-
# Student Telegram bot v2. Settings come from environment variables (see README.txt).
import asyncio
import hashlib
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, filters)

import tools
from i18n import DEFAULT_LANG, LANGS, tr
from tools import DIGITS, UserError

# ───────────────────────── settings ─────────────────────────
def _int_env(name, default=0):
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


TOKEN = os.environ.get("BOT_TOKEN", "")
DAILY_LIMIT = _int_env("DAILY_LIMIT", 3)
TZ = timezone(timedelta(hours=_int_env("TZ_OFFSET", 2)))
MAX_MB = 20
DB_PATH = os.environ.get("DB_PATH", "usage.db")

ADMIN_ID = _int_env("ADMIN_ID")
PAY_ACCOUNT = os.environ.get("PAY_ACCOUNT", "").strip()
PAY_NAME = os.environ.get("PAY_NAME", "").strip()
PAY_PRICE = os.environ.get("PAY_PRICE", "").strip()
PAY_AMOUNT = _int_env("PAY_AMOUNT")
PAY_HOURS = _int_env("PAY_HOURS", 24)
PAY_ENABLED = bool(ADMIN_ID and PAY_ACCOUNT and PAY_PRICE)
# Automatic verification needs the OCR key. PAY_AUTO=0 forces manual approval by the admin.
PAY_AUTO = os.environ.get("PAY_AUTO", "1") != "0" and bool(tools.OCR_API_KEY)
PAY_MAX_TRIES = 3
PAY_MAX_AGE_HOURS = _int_env("PAY_MAX_AGE_HOURS", 48)  # reject older receipts; 0 = off

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger("student_bot")

# ───────────────────────── database ─────────────────────────
def _db(sql, args=(), mode=None):
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.execute(sql, args)
        con.commit()
        if mode == "one":
            return cur.fetchone()
        if mode == "id":
            return cur.lastrowid
        return None
    finally:
        con.close()


def init_db():
    _db("CREATE TABLE IF NOT EXISTS usage (user_id INTEGER, day TEXT, n INTEGER, PRIMARY KEY(user_id, day))")
    _db("CREATE TABLE IF NOT EXISTS passes (user_id INTEGER PRIMARY KEY, until INTEGER)")
    _db("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, "
        "txn TEXT, amount REAL, status TEXT, created INTEGER)")
    _db("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, lang TEXT)")
    try:
        _db("ALTER TABLE payments ADD COLUMN method TEXT")
    except sqlite3.OperationalError:
        pass


_lang_cache = {}


def get_lang(uid):
    if uid in _lang_cache:
        return _lang_cache[uid]
    r = _db("SELECT lang FROM users WHERE user_id=?", (uid,), "one")
    if r and r[0] in LANGS:
        _lang_cache[uid] = r[0]
        return r[0]
    return None


def set_lang(uid, lang):
    _db("INSERT OR REPLACE INTO users(user_id, lang) VALUES(?,?)", (uid, lang))
    _lang_cache[uid] = lang


def L(uid):
    return get_lang(uid) or DEFAULT_LANG


def today():
    return datetime.now(TZ).strftime("%Y-%m-%d")


def used_today(uid):
    r = _db("SELECT n FROM usage WHERE user_id=? AND day=?", (uid, today()), "one")
    return r[0] if r else 0


def add_use(uid):
    _db("INSERT INTO usage(user_id, day, n) VALUES(?,?,1) ON CONFLICT(user_id, day) DO UPDATE SET n = n + 1",
        (uid, today()))


def pass_until(uid):
    r = _db("SELECT until FROM passes WHERE user_id=?", (uid,), "one")
    return r[0] if r else 0


def has_pass(uid):
    return pass_until(uid) > int(time.time())


def remaining(uid):
    return 10**6 if has_pass(uid) else max(0, DAILY_LIMIT - used_today(uid))


def fmt_ts(ts):
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%d %H:%M")


def grant_pass(user_id, hours):
    until = max(int(time.time()), pass_until(user_id)) + hours * 3600
    _db("INSERT OR REPLACE INTO passes(user_id, until) VALUES(?,?)", (user_id, until))
    return until


def quota_text(uid):
    if has_pass(uid):
        return tr(L(uid), "quota_pass", until=fmt_ts(pass_until(uid)))
    return tr(L(uid), "quota_left", n=remaining(uid), limit=DAILY_LIMIT)


# ───────────────────────── tools registry ─────────────────────────
# mode: single | multi | file_then_text | text
TOOLS = {
    "img2pdf": dict(mode="multi", accepts={"image"}, counted=True, fn=tools.f_img2pdf, run="btn_run_pdf"),
    "compress": dict(mode="single", accepts={"image"}, counted=True, fn=tools.f_compress),
    "imgconv": dict(mode="file_then_text", accepts={"image"}, counted=True, fn=tools.f_imgconv),
    "ocr": dict(mode="single", accepts={"image"}, counted=True, fn=tools.f_ocr),
    "pdf_text": dict(mode="single", accepts={"pdf"}, counted=True, fn=tools.f_pdf_text),
    "pdf2word": dict(mode="single", accepts={"pdf"}, counted=True, fn=tools.f_pdf2word),
    "office2pdf": dict(mode="single", accepts={"office"}, counted=True, fn=tools.f_office2pdf),
    "merge": dict(mode="multi", accepts={"pdf"}, counted=True, fn=tools.f_merge, run="btn_run_merge"),
    "split": dict(mode="file_then_text", accepts={"pdf"}, counted=True, fn=tools.f_split),
    "stt_ar": dict(mode="single", accepts={"audio"}, counted=True,
                   fn=lambda f, d, x, l: tools.f_stt(f, d, x, l, "ar-SA")),
    "stt_en": dict(mode="single", accepts={"audio"}, counted=True,
                   fn=lambda f, d, x, l: tools.f_stt(f, d, x, l, "en-US")),
    "tts": dict(mode="text", counted=True, keep=True, fn=tools.f_tts),
    "text2pdf": dict(mode="text", counted=True, fn=tools.f_text2pdf),
    "translate": dict(mode="text", counted=True, keep=True, fn=tools.f_translate),
    "define": dict(mode="text", counted=False, keep=True, fn=tools.f_define),
    "calc": dict(mode="text", counted=False, keep=True, fn=tools.f_calc),
    "gpa": dict(mode="text", counted=False, keep=True, fn=tools.f_gpa),
    "qr": dict(mode="text", counted=False, keep=True, fn=tools.f_qr),
    "units": dict(mode="text", counted=False, keep=True, fn=tools.f_units),
    "quad": dict(mode="text", counted=False, keep=True, fn=tools.f_quad),
    "nums": dict(mode="text", counted=False, keep=True, fn=tools.f_nums),
    "wordcount": dict(mode="text", counted=False, keep=True, fn=tools.f_wordcount),
    "summarize": dict(mode="text", counted=False, keep=True, fn=tools.f_summarize),
    "cite": dict(mode="text", counted=False, keep=True, fn=tools.f_cite),
    "countdown": dict(mode="text", counted=False, keep=True, fn=tools.f_countdown),
    "timer": dict(mode="text", counted=False, keep=True, fn=None),  # handled in on_text
}

SCHOOL = ["img2pdf", "office2pdf", "pdf_text", "ocr", "compress", "imgconv", "text2pdf", "tts",
          "translate", "define", "calc", "quad", "units", "nums", "countdown", "timer", "wordcount", "qr"]
UNI = ["pdf2word", "office2pdf", "merge", "split", "pdf_text", "ocr", "stt_ar", "stt_en", "img2pdf",
       "compress", "imgconv", "text2pdf", "tts", "translate", "define", "summarize", "cite", "gpa",
       "calc", "units", "countdown", "timer", "wordcount", "qr"]

EXT_KINDS = {
    "image": {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"},
    "office": {".docx", ".pptx", ".xlsx", ".txt"},
    "audio": {".mp3", ".wav", ".ogg", ".oga", ".opus", ".m4a", ".aac", ".flac", ".amr"},
}


def kind_of(name, mime=""):
    ext = Path(name).suffix.lower()
    if ext in EXT_KINDS["image"] or mime.startswith("image/"):
        return "image"
    if ext == ".pdf" or mime == "application/pdf":
        return "pdf"
    if ext in EXT_KINDS["office"]:
        return "office"
    if ext in EXT_KINDS["audio"] or mime.startswith("audio/"):
        return "audio"
    return None


# ───────────────────────── keyboards ─────────────────────────
def B(text, data):
    return InlineKeyboardButton(text, callback_data=data)


def kb_home(uid):
    lg = L(uid)
    rows = [[B(tr(lg, "btn_school"), "menu:school")], [B(tr(lg, "btn_uni"), "menu:uni")],
            [B(tr(lg, "btn_quota"), "quota"), B(tr(lg, "btn_lang"), "lang:pick")]]
    if PAY_ENABLED:
        rows.append([B(tr(lg, "btn_pay"), "pay:start")])
    return InlineKeyboardMarkup(rows)


def kb_menu(uid, kind):
    lg = L(uid)
    keys = SCHOOL if kind == "school" else UNI
    rows, row = [], []
    for k in keys:
        row.append(B(tr(lg, f"t_{k}"), f"tool:{k}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([B(tr(lg, "btn_home"), "menu:home")])
    return InlineKeyboardMarkup(rows)


def kb_back(uid):
    return InlineKeyboardMarkup([[B(tr(L(uid), "btn_home"), "menu:home")]])


def kb_cancel(uid):
    return InlineKeyboardMarkup([[B(tr(L(uid), "btn_cancel"), "cancel")]])


def kb_run(uid, label_key):
    lg = L(uid)
    return InlineKeyboardMarkup([[B(tr(lg, label_key), "run")], [B(tr(lg, "btn_cancel"), "cancel")]])


def kb_limit(uid):
    rows = []
    if PAY_ENABLED:
        rows.append([B(tr(L(uid), "btn_pay_buy"), "pay:start")])
    rows.append([B(tr(L(uid), "btn_home"), "menu:home")])
    return InlineKeyboardMarkup(rows)


def kb_langs():
    return InlineKeyboardMarkup([[B(name, f"lang:{code}")] for code, name in LANGS.items()])


def limit_text(uid):
    t = tr(L(uid), "limit", limit=DAILY_LIMIT)
    if PAY_ENABLED:
        t += tr(L(uid), "limit_pay", hours=PAY_HOURS)
    return t


# ───────────────────────── state ─────────────────────────
def reset_state(context):
    d = context.user_data.get("dir")
    if d:
        shutil.rmtree(d, ignore_errors=True)
    context.user_data.clear()


async def send_result(msg, typ, val):
    if typ == "text":
        for i in range(0, len(val), 4000):
            await msg.reply_text(val[i:i + 4000])
        return
    with open(val, "rb") as f:
        if typ == "file":
            await msg.reply_document(f, filename=Path(val).name)
        elif typ == "audio":
            await msg.reply_audio(f, filename=Path(val).name)
        elif typ == "photo":
            await msg.reply_photo(f)


_bg_tasks = set()


async def run_timer(bot, chat_id, minutes, lg):
    await asyncio.sleep(minutes * 60)
    try:
        await bot.send_message(chat_id, tr(lg, "r_timer_done", m=minutes))
    except Exception:
        log.exception("timer notify failed")


async def execute(msg, uid, context, extra=None):
    ud, lg = context.user_data, L(uid)
    key = ud.get("tool")
    if not key:
        await msg.reply_text(tr(lg, "pick_tool_first"), reply_markup=kb_home(uid))
        return
    tool = TOOLS[key]
    if ud.get("busy"):
        await msg.reply_text(tr(lg, "busy"))
        return
    if tool["counted"] and remaining(uid) <= 0:
        await msg.reply_text(limit_text(uid), reply_markup=kb_limit(uid))
        reset_state(context)
        return
    if tool["mode"] == "multi" and not ud.get("files"):
        await msg.reply_text(tr(lg, "no_files"))
        return

    if key == "timer":
        nums = re.findall(r"\d+", (extra or "").translate(DIGITS))
        if not nums or not 1 <= int(nums[0]) <= 180:
            await msg.reply_text("⚠️ " + tr(lg, "e_timer"))
            return
        minutes = int(nums[0])
        task = asyncio.create_task(run_timer(context.bot, msg.chat_id, minutes, lg))
        _bg_tasks.add(task)
        task.add_done_callback(_bg_tasks.discard)
        await msg.reply_text(tr(lg, "r_timer_set", m=minutes), reply_markup=kb_back(uid))
        return

    ud["busy"] = True
    status = await msg.reply_text(tr(lg, "processing"))
    ok = fatal = False
    try:
        files = [Path(p) for p in ud.get("files", [])]
        results = await asyncio.to_thread(tool["fn"], files, Path(ud["dir"]), extra, lg)
        for typ, val in results:
            await send_result(msg, typ, val)
        ok = True
    except UserError as e:
        await msg.reply_text("⚠️ " + tr(lg, e.key, **e.kw))
    except Exception:
        log.exception("tool %s failed", key)
        fatal = True
        await msg.reply_text(tr(lg, "err_generic"))
    finally:
        ud["busy"] = False
        try:
            await status.delete()
        except Exception:
            pass

    if ok and tool["counted"]:
        add_use(uid)
    if ok:
        tail = f"\n{quota_text(uid)}" if tool["counted"] else ""
        if tool.get("keep"):
            await msg.reply_text(f"{tr(lg, 'done')}{tail}\n{tr(lg, 'more_or_menu')}", reply_markup=kb_back(uid))
        else:
            reset_state(context)
            await msg.reply_text(f"{tr(lg, 'done')}{tail}", reply_markup=kb_back(uid))
    elif fatal:
        reset_state(context)
        await msg.reply_text(tr(lg, "pick_tool_again"), reply_markup=kb_home(uid))


# ───────────────────────── commands ─────────────────────────
async def send_welcome(msg, uid):
    await msg.reply_text(tr(L(uid), "welcome", limit=DAILY_LIMIT), reply_markup=kb_home(uid))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)
    uid = update.effective_user.id
    if get_lang(uid) is None:
        await update.message.reply_text(tr("ar", "choose_lang"), reply_markup=kb_langs())
        return
    await send_welcome(update.message, uid)


async def quota_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(quota_text(uid), reply_markup=kb_back(uid))


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    reset_state(context)
    await update.message.reply_text(tr(L(uid), "cancelled"), reply_markup=kb_home(uid))


async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(tr("ar", "choose_lang"), reply_markup=kb_langs())


async def myid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"ID: {update.effective_user.id}")


async def grant_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        uid = int(context.args[0])
        hours = int(context.args[1]) if len(context.args) > 1 else PAY_HOURS
    except (IndexError, ValueError):
        await update.message.reply_text("/grant USER_ID [HOURS]")
        return
    await update.message.reply_text(f"OK → {fmt_ts(grant_pass(uid, hours))}")


# ───────────────────────── buttons ─────────────────────────
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data, uid = q.data, q.from_user.id

    if data.startswith("pay:"):
        await pay_button(q, context)
        return
    if data.startswith("lang:"):
        code = data[5:]
        if code == "pick":
            await q.message.reply_text(tr("ar", "choose_lang"), reply_markup=kb_langs())
        elif code in LANGS:
            set_lang(uid, code)
            reset_state(context)
            await q.message.reply_text(tr(code, "lang_set"))
            await send_welcome(q.message, uid)
        return

    lg = L(uid)
    if data == "menu:home":
        reset_state(context)
        await q.message.reply_text(tr(lg, "pick_section"), reply_markup=kb_home(uid))
    elif data in ("menu:school", "menu:uni"):
        reset_state(context)
        kind = data.split(":")[1]
        await q.message.reply_text(tr(lg, "title_school" if kind == "school" else "title_uni"),
                                   reply_markup=kb_menu(uid, kind))
    elif data == "quota":
        await q.message.reply_text(quota_text(uid), reply_markup=kb_back(uid))
    elif data == "cancel":
        reset_state(context)
        await q.message.reply_text(tr(lg, "cancelled"), reply_markup=kb_home(uid))
    elif data == "run":
        await execute(q.message, uid, context)
    elif data.startswith("tool:"):
        key = data[5:]
        tool = TOOLS.get(key)
        if not tool:
            return
        if tool["counted"] and remaining(uid) <= 0:
            await q.message.reply_text(limit_text(uid), reply_markup=kb_limit(uid))
            return
        reset_state(context)
        context.user_data.update(tool=key, files=[], dir=tempfile.mkdtemp(prefix="stbot_"))
        await q.message.reply_text(tr(lg, f"p_{key}"), reply_markup=kb_cancel(uid))


# ───────────────────────── incoming files and text ─────────────────────────
async def on_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg, ud = update.message, context.user_data
    uid = msg.from_user.id
    lg = L(uid)
    if ud.get("pay"):
        await pay_media(update, context)
        return
    key = ud.get("tool")
    if not key:
        await msg.reply_text(tr(lg, "pick_tool_first"), reply_markup=kb_home(uid))
        return
    tool = TOOLS[key]
    if tool["mode"] == "text":
        await msg.reply_text(tr(lg, "text_only"))
        return
    if ud.get("busy"):
        await msg.reply_text(tr(lg, "busy"))
        return

    if msg.photo:
        obj, name, kind = msg.photo[-1], f"photo_{msg.photo[-1].file_unique_id}.jpg", "image"
    elif msg.document:
        obj = msg.document
        name = obj.file_name or "file"
        kind = kind_of(name, obj.mime_type or "")
    elif msg.voice:
        obj, name, kind = msg.voice, "voice.ogg", "audio"
    elif msg.audio:
        obj, name, kind = msg.audio, obj_name(msg.audio), "audio"
    else:
        return

    if kind not in tool["accepts"]:
        need = " / ".join(tr(lg, f"k_{k}") for k in tool["accepts"])
        await msg.reply_text(tr(lg, "wrong_type", need=need))
        return
    if obj.file_size and obj.file_size > MAX_MB * 1024 * 1024:
        await msg.reply_text(tr(lg, "too_big", mb=MAX_MB))
        return
    if tool["mode"] == "multi" and len(ud["files"]) >= 20:
        await msg.reply_text(tr(lg, "max_files"))
        return

    safe = re.sub(r"[^\w.\-]", "_", Path(name).name)
    path = Path(ud["dir"]) / f"{len(ud['files']):03d}_{safe}"
    try:
        tgfile = await obj.get_file()
        await tgfile.download_to_drive(str(path))
    except Exception:
        log.exception("download failed")
        await msg.reply_text(tr(lg, "dl_fail"))
        return

    if tool["mode"] == "multi":
        ud["files"].append(str(path))
        await msg.reply_text(tr(lg, "got_files", n=len(ud["files"])), reply_markup=kb_run(uid, tool["run"]))
    elif tool["mode"] == "file_then_text":
        ud["files"] = [str(path)]
        await msg.reply_text(tr(lg, f"a_{key}"), reply_markup=kb_cancel(uid))
    else:
        ud["files"] = [str(path)]
        await execute(msg, uid, context)


def obj_name(audio):
    return audio.file_name or "audio.mp3"


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg, ud = update.message, context.user_data
    uid = msg.from_user.id
    lg = L(uid)
    if ud.get("pay"):
        await pay_text(update, context)
        return
    key = ud.get("tool")
    if not key:
        if get_lang(uid) is None:
            await msg.reply_text(tr("ar", "choose_lang"), reply_markup=kb_langs())
        else:
            await msg.reply_text(tr(lg, "pick_tool_first"), reply_markup=kb_home(uid))
        return
    tool = TOOLS[key]
    if tool["mode"] == "text" or (tool["mode"] == "file_then_text" and ud.get("files")):
        await execute(msg, uid, context, extra=msg.text)
    elif tool["mode"] == "file_then_text":
        await msg.reply_text(tr(lg, "send_file_first"))
    else:
        await msg.reply_text(tr(lg, "file_only"))


# ───────────────────────── payment: open day pass ─────────────────────────
def admin_kb(pid, can_review=True):
    if can_review:
        return InlineKeyboardMarkup([[B("✅ قبول", f"pay:ok:{pid}"), B("❌ رفض", f"pay:no:{pid}")]])
    return InlineKeyboardMarkup([[B("🚫 إلغاء التفعيل", f"pay:rv:{pid}")]])


async def pay_button(q, context):
    data, uid = q.data, q.from_user.id
    lg = L(uid)

    if data == "pay:start":
        if not PAY_ENABLED:
            await q.message.reply_text(tr(lg, "pay_off"))
            return
        reset_state(context)
        name_line = tr(lg, "pay_name_line", name=PAY_NAME) if PAY_NAME else ""
        await q.message.reply_text(
            tr(lg, "pay_info", hours=PAY_HOURS, price=PAY_PRICE, account=PAY_ACCOUNT, name_line=name_line),
            reply_markup=InlineKeyboardMarkup([[B(tr(lg, "pay_btn_sent"), "pay:sent")],
                                               [B(tr(lg, "btn_home"), "menu:home")]]))

    elif data == "pay:sent":
        if not PAY_ENABLED:
            return
        reset_state(context)
        context.user_data["pay"] = {"step": "txn", "tries": 0}
        await q.message.reply_text(tr(lg, "pay_ask_txn"), reply_markup=kb_cancel(uid))

    elif data.startswith(("pay:ok:", "pay:no:", "pay:rv:")):
        if uid != ADMIN_ID:
            return
        action, pid = data.split(":")[1], int(data.split(":")[2])
        row = _db("SELECT user_id, status FROM payments WHERE id=?", (pid,), "one")
        if not row:
            return
        user_id, status = row
        ulg = L(user_id)
        note = mark = None
        if action == "rv":
            _db("UPDATE payments SET status='revoked' WHERE id=?", (pid,))
            _db("DELETE FROM passes WHERE user_id=?", (user_id,))
            note, mark = tr(ulg, "pay_revoked"), "🚫 تم إلغاء التفعيل"
        elif status in ("pending", "rejected"):
            if action == "ok":
                until = grant_pass(user_id, PAY_HOURS)
                _db("UPDATE payments SET status='approved', method='admin' WHERE id=?", (pid,))
                note, mark = tr(ulg, "pay_approved_manual", until=fmt_ts(until)), "✅ تم القبول"
            else:
                _db("UPDATE payments SET status='rejected' WHERE id=?", (pid,))
                note, mark = tr(ulg, "pay_rejected_manual"), "❌ تم الرفض"
        if note:
            try:
                await context.bot.send_message(user_id, note)
            except Exception:
                log.exception("notify user failed")
            try:
                await q.edit_message_caption(
                    caption=(q.message.caption or "") + "\n\n" + mark,
                    reply_markup=admin_kb(pid, False) if mark.startswith("✅") else None)
            except Exception:
                pass


def _pay_reply(msg, lg, key, **kw):
    return msg.reply_text(tr(lg, key, **kw))


async def pay_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg, p = update.message, context.user_data["pay"]
    uid = msg.from_user.id
    lg = L(uid)
    text = (msg.text or "").strip().translate(DIGITS)

    if p["step"] == "txn":
        txn = re.sub(r"\s+", "", text).lower()
        if not 5 <= len(txn) <= 40:
            await _pay_reply(msg, lg, "pay_bad_txn")
            return
        used = _db("SELECT 1 FROM payments WHERE txn=? AND status IN ('pending','approved')", (txn,), "one")
        if used:
            await _pay_reply(msg, lg, "pay_dup_txn")
            return
        p["txn"], p["step"] = txn, "amount"
        await msg.reply_text(tr(lg, "pay_ask_amount"), reply_markup=kb_cancel(uid))
    elif p["step"] == "amount":
        nums = re.findall(r"\d+(?:\.\d+)?", text.replace(",", "").replace("،", ""))
        if not nums:
            await _pay_reply(msg, lg, "pay_bad_amount")
            return
        amount = float(nums[0])
        if PAY_AMOUNT and amount < PAY_AMOUNT:
            await _pay_reply(msg, lg, "pay_low_amount", price=PAY_PRICE)
            return
        p["amount"], p["step"] = amount, "photo"
        await msg.reply_text(tr(lg, "pay_ask_photo"), reply_markup=kb_cancel(uid))
    else:
        await _pay_reply(msg, lg, "pay_ask_photo")


async def notify_admin_photo(bot, file_id, caption, kb):
    try:
        await bot.send_photo(ADMIN_ID, file_id, caption=caption, reply_markup=kb)
        return True
    except Exception:
        log.exception("send to admin failed")
        return False


async def pay_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg, ud = update.message, context.user_data
    p = ud["pay"]
    u = msg.from_user
    lg = L(u.id)
    if p["step"] != "photo" or not msg.photo:
        what = {"txn": "pay_w_txn", "amount": "pay_w_amount"}.get(p["step"], "pay_w_photo")
        await msg.reply_text(tr(lg, "pay_order_hint", what=tr(lg, what)))
        return
    if ud.get("busy"):
        return
    if _db("SELECT 1 FROM payments WHERE user_id=? AND status='pending'", (u.id,), "one"):
        reset_state(context)
        await msg.reply_text(tr(lg, "pay_pending"), reply_markup=kb_back(u.id))
        return
    # the same txn may have been used by someone else while this user was typing
    if _db("SELECT 1 FROM payments WHERE txn=? AND status IN ('pending','approved')", (p["txn"],), "one"):
        reset_state(context)
        await msg.reply_text(tr(lg, "pay_dup_txn"), reply_markup=kb_back(u.id))
        return

    photo = msg.photo[-1]
    who = f"{u.full_name} (@{u.username or '-'}) id={u.id}"
    base_cap = f"المستخدم: {who}\nرقم العملية: {p['txn']}\nالمبلغ: {p['amount']:g}"

    # ── manual mode (no OCR key, or PAY_AUTO=0): the admin decides ──
    if not PAY_AUTO:
        pid = _db("INSERT INTO payments(user_id, txn, amount, status, created, method) VALUES(?,?,?,?,?,?)",
                  (u.id, p["txn"], p["amount"], "pending", int(time.time()), "manual"), "id")
        cap = f"💳 طلب دفع #{pid}\n{base_cap}\n\nتحقق في تطبيق بنكك من وصول المبلغ قبل القبول."
        if not await notify_admin_photo(context.bot, photo.file_id, cap, admin_kb(pid)):
            _db("DELETE FROM payments WHERE id=?", (pid,))
            await msg.reply_text(tr(lg, "err_generic"))
            return
        reset_state(context)
        await msg.reply_text(tr(lg, "pay_manual_wait"), reply_markup=kb_back(u.id))
        return

    # ── automatic mode: read the receipt and decide ──
    ud["busy"] = True
    status = await msg.reply_text(tr(lg, "pay_checking"))
    ok, reason = False, "why_ocr"
    try:
        if not ud.get("dir"):
            ud["dir"] = tempfile.mkdtemp(prefix="stbot_")
        path = Path(ud["dir"]) / "receipt.jpg"
        tgfile = await photo.get_file()
        await tgfile.download_to_drive(str(path))
        text = await asyncio.to_thread(tools.ocr_text, path, ("ara", "eng"))
        if text.strip():
            ok, reason = tools.check_receipt(text, p["txn"], p["amount"], PAY_ACCOUNT, PAY_NAME,
                                             PAY_MAX_AGE_HOURS)
    except Exception:
        log.exception("receipt check failed")
    finally:
        ud["busy"] = False
        try:
            await status.delete()
        except Exception:
            pass

    if ok:
        pid = _db("INSERT INTO payments(user_id, txn, amount, status, created, method) VALUES(?,?,?,?,?,?)",
                  (u.id, p["txn"], p["amount"], "approved", int(time.time()), "auto"), "id")
        until = grant_pass(u.id, PAY_HOURS)
        reset_state(context)
        await msg.reply_text(tr(lg, "pay_ok", until=fmt_ts(until)), reply_markup=kb_back(u.id))
        cap = (f"✅ قُبل تلقائياً #{pid}\n{base_cap}\nحتى: {fmt_ts(until)}\n\n"
               "إن شككت في الإشعار فاضغط «إلغاء التفعيل».")
        await notify_admin_photo(context.bot, photo.file_id, cap, admin_kb(pid, False))
        return

    p["tries"] = p.get("tries", 0) + 1
    if p["tries"] < PAY_MAX_TRIES:
        await msg.reply_text(tr(lg, "pay_retry", reason=tr(lg, reason), n=p["tries"] + 1, mx=PAY_MAX_TRIES),
                             reply_markup=kb_cancel(u.id))
        return

    # attempts used up: reject, but give the admin a one-tap override for honest students
    pid = _db("INSERT INTO payments(user_id, txn, amount, status, created, method) VALUES(?,?,?,?,?,?)",
              (u.id, p["txn"], p["amount"], "rejected", int(time.time()), "auto"), "id")
    reset_state(context)
    await msg.reply_text(tr(lg, "pay_reject", reason=tr(lg, reason)), reply_markup=kb_back(u.id))
    cap = (f"❌ رُفض تلقائياً #{pid} ({tr('ar', reason)})\n{base_cap}\n\n"
           "إن كان الطالب صادقاً وتأكدت من بنكك فاضغط «قبول».")
    await notify_admin_photo(context.bot, photo.file_id, cap, admin_kb(pid))


async def on_error(update, context: ContextTypes.DEFAULT_TYPE):
    log.error("Unhandled error", exc_info=context.error)


def main():
    if not TOKEN:
        raise SystemExit("Set the BOT_TOKEN environment variable")
    init_db()
    app = (Application.builder().token(TOKEN).concurrent_updates(True)
           .connect_timeout(30).read_timeout(60).write_timeout(120).build())
    app.add_handler(CommandHandler(["start", "menu"], start))
    app.add_handler(CommandHandler("quota", quota_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CommandHandler("myid", myid_cmd))
    app.add_handler(CommandHandler("grant", grant_cmd))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL | filters.VOICE | filters.AUDIO, on_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)
    log.info("Bot started (payments=%s, auto-verify=%s)", PAY_ENABLED, PAY_AUTO)
    asyncio.set_event_loop(asyncio.new_event_loop())  # needed on Python 3.14
    app.run_polling()


if __name__ == "__main__":
    main()
