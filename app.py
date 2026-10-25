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
TOKEN = os.environ.get("BOT_TOKEN", "")
DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT", "3"))
TZ = timezone(timedelta(hours=int(os.environ.get("TZ_OFFSET", "2"))))  # توقيت إعادة تصفير الحد
MAX_MB = 20  # أقصى حجم يسمح تيليجرام للبوت بتنزيله
DB_PATH = os.environ.get("DB_PATH", "usage.db")

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger("student_bot")


class UserError(Exception):
    """خطأ يُعرض للمستخدم كما هو."""


# ───────────────────────── قاعدة بيانات الحد اليومي ─────────────────────────
def _db(sql, args=(), fetch=False):
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.execute(sql, args)
        con.commit()
        return cur.fetchone() if fetch else None
    finally:
        con.close()


def init_db():
    _db(
        "CREATE TABLE IF NOT EXISTS usage "
        "(user_id INTEGER, day TEXT, n INTEGER, PRIMARY KEY(user_id, day))"
    )


def today():
    return datetime.now(TZ).strftime("%Y-%m-%d")


def used_today(uid):
    r = _db("SELECT n FROM usage WHERE user_id=? AND day=?", (uid, today()), fetch=True)
    return r[0] if r else 0


def remaining(uid):
    return max(0, DAILY_LIMIT - used_today(uid))


def add_use(uid):
    _db(
        "INSERT INTO usage(user_id, day, n) VALUES(?,?,1) "
        "ON CONFLICT(user_id, day) DO UPDATE SET n = n + 1",
        (uid, today()),
    )


# ───────────────────────── أدوات مساعدة ─────────────────────────
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
OFFICE_EXT = {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".odt", ".odp", ".ods", ".rtf", ".txt"}
AUDIO_EXT = {".mp3", ".wav", ".ogg", ".oga", ".opus", ".m4a", ".aac", ".flac", ".amr"}
KIND_NAMES = {
    "image": "صورة",
    "pdf": "ملف PDF",
    "office": "ملف Word / PowerPoint / Excel",
    "audio": "ملف صوتي أو رسالة صوتية",
}


def kind_of(name, mime=""):
    ext = Path(name).suffix.lower()
    if ext in IMG_EXT or mime.startswith("image/"):
        return "image"
    if ext == ".pdf" or mime == "application/pdf":
        return "pdf"
    if ext in OFFICE_EXT:
        return "office"
    if ext in AUDIO_EXT or mime.startswith("audio/"):
        return "audio"
    return None


def clean_stem(p: Path):
    return re.sub(r"^\d{3}_", "", p.stem) or "file"


def to_rgb(im):
    from PIL import Image, ImageOps

    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert("RGB")


# ───────────────────────── الأدوات ─────────────────────────
# كل أداة: fn(files, workdir, extra) -> [("file"|"text"|"audio"|"photo", قيمة), ...]

def f_img2pdf(files, d, extra):
    from PIL import Image

    imgs = [to_rgb(Image.open(p)) for p in files]
    out = d / "images.pdf"
    imgs[0].save(out, save_all=True, append_images=imgs[1:])
    return [("file", out)]


def f_compress(files, d, extra):
    from PIL import Image

    im = to_rgb(Image.open(files[0]))
    im.thumbnail((1600, 1600))
    out = d / f"{clean_stem(files[0])}_small.jpg"
    im.save(out, "JPEG", quality=60, optimize=True)
    before = files[0].stat().st_size // 1024
    after = out.stat().st_size // 1024
    return [("file", out), ("text", f"الحجم: {before} KB ← {after} KB")]


def f_ocr(files, d, extra):
    if not shutil.which("tesseract"):
        raise UserError("محرك قراءة النصوص (OCR) غير مثبت على الخادم.")
    import pytesseract
    from PIL import Image, ImageOps

    im = ImageOps.exif_transpose(Image.open(files[0])).convert("L")
    text = pytesseract.image_to_string(im, lang="ara+eng").strip()
    if not text:
        raise UserError("لم أجد نصاً واضحاً في الصورة. جرّب صورة أوضح وبإضاءة جيدة.")
    return [("text", text)]


def f_pdf_text(files, d, extra):
    from pypdf import PdfReader

    reader = PdfReader(str(files[0]))
    if reader.is_encrypted:
        raise UserError("الملف محمي بكلمة مرور.")
    text = "\n\n".join((pg.extract_text() or "") for pg in reader.pages).strip()
    if not text:
        raise UserError("الملف لا يحتوي نصاً (غالباً ممسوح ضوئياً). حوّل صفحاته إلى صور واستخدم أداة «صورة ← نص».")
    if len(text) <= 3500:
        return [("text", text)]
    out = d / f"{clean_stem(files[0])}.txt"
    out.write_text(text, encoding="utf-8")
    return [("file", out)]


def f_pdf2word(files, d, extra):
    from pdf2docx import Converter

    out = d / f"{clean_stem(files[0])}.docx"
    cv = Converter(str(files[0]))
    try:
        cv.convert(str(out))
    finally:
        cv.close()
    return [("file", out)]


def f_office2pdf(files, d, extra):
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        raise UserError("أداة التحويل (LibreOffice) غير مثبتة على الخادم.")
    src = files[0]
    subprocess.run(
        [exe, "--headless", f"-env:UserInstallation=file://{d}/lo_profile",
         "--convert-to", "pdf", "--outdir", str(d), str(src)],
        check=True, capture_output=True, timeout=180,
    )
    out = d / f"{src.stem}.pdf"
    if not out.exists():
        raise UserError("فشل التحويل.")
    return [("file", out)]


def f_merge(files, d, extra):
    from pypdf import PdfWriter

    if len(files) < 2:
        raise UserError("أرسل ملفين PDF على الأقل ثم اضغط «دمج».")
    w = PdfWriter()
    for p in files:
        w.append(str(p))
    out = d / "merged.pdf"
    with open(out, "wb") as f:
        w.write(f)
    return [("file", out)]


def parse_pages(s, n):
    s = s.translate(DIGITS)
    pages = []
    for part in re.split(r"[,\u060c\s]+", s.strip()):
        if not part:
            continue
        try:
            if "-" in part:
                a, b = part.split("-", 1)
                rng = range(int(a), int(b) + 1)
            else:
                rng = [int(part)]
        except ValueError:
            raise UserError("صيغة غير صحيحة. مثال: 1-3 أو 2,5,7-9")
        for x in rng:
            if not 1 <= x <= n:
                raise UserError(f"الصفحة {x} خارج النطاق. عدد صفحات الملف: {n}")
            pages.append(x - 1)
    if not pages:
        raise UserError("أرسل أرقام الصفحات. مثال: 1-3 أو 2,5,7-9")
    return pages


def f_split(files, d, extra):
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(files[0]))
    pages = parse_pages(extra or "", len(reader.pages))
    w = PdfWriter()
    for i in pages:
        w.add_page(reader.pages[i])
    out = d / f"{clean_stem(files[0])}_pages.pdf"
    with open(out, "wb") as f:
        w.write(f)
    return [("file", out)]


def f_stt(files, d, extra, lang):
    if not shutil.which("ffmpeg"):
        raise UserError("ffmpeg غير مثبت على الخادم.")
    import speech_recognition as sr

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(files[0]), "-vn", "-ar", "16000", "-ac", "1",
         "-f", "segment", "-segment_time", "45", str(d / "chunk_%03d.wav")],
        check=True, capture_output=True, timeout=300,
    )
    chunks = sorted(d.glob("chunk_*.wav"))
    if not chunks:
        raise UserError("تعذرت قراءة الملف الصوتي.")
    if len(chunks) > 20:
        raise UserError("التسجيل طويل جداً (الحد الأقصى نحو 15 دقيقة).")
    r = sr.Recognizer()
    parts = []
    for c in chunks:
        with sr.AudioFile(str(c)) as s:
            audio = r.record(s)
        try:
            parts.append(r.recognize_google(audio, language=lang))
        except sr.UnknownValueError:
            pass
        except sr.RequestError:
            raise UserError("تعذر الاتصال بخدمة التعرف على الصوت، حاول لاحقاً.")
    text = " ".join(parts).strip()
    if not text:
        raise UserError("لم أستطع استخراج كلام واضح من التسجيل.")
    return [("text", text)]


def f_tts(files, d, extra):
    from gtts import gTTS

    text = (extra or "").strip()
    if not text:
        raise UserError("أرسل النص الذي تريد تحويله إلى صوت.")
    if len(text) > 1000:
        raise UserError("النص طويل (الحد 1000 حرف).")
    lang = "ar" if re.search(r"[\u0600-\u06FF]", text) else "en"
    out = d / "speech.mp3"
    gTTS(text, lang=lang).save(str(out))
    return [("audio", out)]


def f_qr(files, d, extra):
    import qrcode

    text = (extra or "").strip()
    if not text:
        raise UserError("أرسل النص أو الرابط.")
    out = d / "qr.png"
    qrcode.make(text).save(out)
    return [("photo", out)]


# حاسبة آمنة (الزوايا بالدرجات)
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos,
}
_FUNCS = {
    "sqrt": math.sqrt, "abs": abs, "log": math.log10, "ln": math.log,
    "sin": lambda x: math.sin(math.radians(x)),
    "cos": lambda x: math.cos(math.radians(x)),
    "tan": lambda x: math.tan(math.radians(x)),
}
_CONST = {"pi": math.pi, "e": math.e}


def _ev(n):
    if isinstance(n, ast.Expression):
        return _ev(n.body)
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        return n.value
    if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
        a, b = _ev(n.left), _ev(n.right)
        if isinstance(n.op, ast.Pow) and abs(b) > 1000:
            raise UserError("الأس كبير جداً.")
        return _OPS[type(n.op)](a, b)
    if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
        return _OPS[type(n.op)](_ev(n.operand))
    if isinstance(n, ast.Name) and n.id in _CONST:
        return _CONST[n.id]
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and len(n.args) == 1:
        return _FUNCS[n.func.id](_ev(n.args[0]))
    raise UserError("لم أفهم العملية. مثال: (5+3)*2^3 أو sqrt(144) أو sin(30)")


def f_calc(files, d, extra):
    expr = (extra or "").translate(DIGITS).replace("×", "*").replace("÷", "/").replace("^", "**")
    try:
        val = _ev(ast.parse(expr.strip(), mode="eval"))
    except UserError:
        raise
    except ZeroDivisionError:
        raise UserError("لا يمكن القسمة على صفر.")
    except (SyntaxError, ValueError, OverflowError, TypeError):
        raise UserError("لم أفهم العملية. مثال: (5+3)*2^3 أو sqrt(144) أو sin(30)")
    if isinstance(val, float):
        val = round(val, 10)
        if val.is_integer():
            val = int(val)
    return [("text", f"= {val}")]


def f_gpa(files, d, extra):
    total_pts = total_hrs = 0.0
    for line in (extra or "").translate(DIGITS).splitlines():
        nums = re.findall(r"\d+(?:\.\d+)?", line)
        if len(nums) < 2:
            continue
        pts, hrs = float(nums[0]), float(nums[1])
        total_pts += pts * hrs
        total_hrs += hrs
    if total_hrs == 0:
        raise UserError("اكتب كل مادة في سطر: النقاط ثم الساعات. مثال:\n4 3\n3.5 2\n3 4")
    return [("text", f"المعدل التراكمي: {total_pts / total_hrs:.2f}\nمجموع الساعات: {total_hrs:g}")]


# ───────────────────────── تعريف الأدوات والأقسام ─────────────────────────
# mode: single = ملف واحد ينفذ فوراً | multi = عدة ملفات ثم زر | file_then_text = ملف ثم نص | text = نص فقط
TOOLS = {
    "img2pdf": dict(title="📷 صور ← PDF", mode="multi", accepts={"image"}, counted=True, fn=f_img2pdf,
                    prompt="أرسل الصور (واحدة تلو الأخرى) ثم اضغط «إنشاء PDF».", run_label="✅ إنشاء PDF"),
    "compress": dict(title="🗜 ضغط صورة", mode="single", accepts={"image"}, counted=True, fn=f_compress,
                     prompt="أرسل الصورة التي تريد تصغير حجمها."),
    "ocr": dict(title="🔍 صورة ← نص", mode="single", accepts={"image"}, counted=True, fn=f_ocr,
                prompt="أرسل صورة فيها نص (كتاب، سبورة، ملاحظات) لاستخراج النص."),
    "pdf_text": dict(title="📄 PDF ← نص", mode="single", accepts={"pdf"}, counted=True, fn=f_pdf_text,
                     prompt="أرسل ملف PDF لاستخراج نصه."),
    "pdf2word": dict(title="📝 PDF ← Word", mode="single", accepts={"pdf"}, counted=True, fn=f_pdf2word,
                     prompt="أرسل ملف PDF لتحويله إلى Word."),
    "office2pdf": dict(title="📑 Word/PPT/Excel ← PDF", mode="single", accepts={"office"}, counted=True,
                       fn=f_office2pdf, prompt="أرسل ملف Word أو PowerPoint أو Excel لتحويله إلى PDF."),
    "merge": dict(title="🧷 دمج PDF", mode="multi", accepts={"pdf"}, counted=True, fn=f_merge,
                  prompt="أرسل ملفات PDF بالترتيب المطلوب ثم اضغط «دمج».", run_label="✅ دمج"),
    "split": dict(title="✂️ استخراج صفحات PDF", mode="file_then_text", accepts={"pdf"}, counted=True, fn=f_split,
                  prompt="أرسل ملف PDF.", ask="أرسل أرقام الصفحات المطلوبة. مثال: 1-3 أو 2,5,7-9"),
    "stt_ar": dict(title="🎙 صوت ← نص (عربي)", mode="single", accepts={"audio"}, counted=True,
                   fn=lambda f, d, x: f_stt(f, d, x, "ar-SA"),
                   prompt="أرسل رسالة صوتية أو ملفاً صوتياً (عربي)."),
    "stt_en": dict(title="🎙 صوت ← نص (English)", mode="single", accepts={"audio"}, counted=True,
                   fn=lambda f, d, x: f_stt(f, d, x, "en-US"),
                   prompt="أرسل رسالة صوتية أو ملفاً صوتياً (إنجليزي)."),
    "tts": dict(title="🔊 نص ← صوت", mode="text", counted=True, keep=True, fn=f_tts,
                prompt="أرسل النص الذي تريد سماعه (عربي أو إنجليزي)."),
    "calc": dict(title="🧮 حاسبة علمية", mode="text", counted=False, keep=True, fn=f_calc,
                 prompt="أرسل العملية. أمثلة: (5+3)*2^3 ، sqrt(144) ، sin(30) ، log(1000)\n(مجانية بلا حد)"),
    "gpa": dict(title="🎓 حاسبة المعدل", mode="text", counted=False, keep=True, fn=f_gpa,
                prompt="اكتب كل مادة في سطر: النقاط ثم الساعات.\nمثال:\n4 3\n3.5 2\n3 4\n(مجانية بلا حد)"),
    "qr": dict(title="🔳 إنشاء QR", mode="text", counted=False, keep=True, fn=f_qr,
               prompt="أرسل النص أو الرابط لإنشاء رمز QR. (مجاني بلا حد)"),
}

SCHOOL = ["img2pdf", "office2pdf", "pdf_text", "ocr", "compress", "tts", "calc", "qr"]
UNI = ["pdf2word", "office2pdf", "merge", "split", "pdf_text", "ocr", "stt_ar", "stt_en",
       "img2pdf", "compress", "tts", "gpa", "calc", "qr"]

# وضع خفيف للاستضافة المجانية (ذاكرة قليلة): LITE=1 يخفي الأدوات الثقيلة
LITE = os.environ.get("LITE", "0") == "1"
HEAVY = {"ocr", "stt_ar", "stt_en", "pdf2word", "office2pdf"}
if LITE:
    SCHOOL = [k for k in SCHOOL if k not in HEAVY]
    UNI = [k for k in UNI if k not in HEAVY]


# ───────────────────────── لوحات الأزرار ─────────────────────────
def kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎒 طالب مدرسي", callback_data="menu:school")],
        [InlineKeyboardButton("🎓 طالب جامعي", callback_data="menu:uni")],
        [InlineKeyboardButton("📊 رصيدي اليوم", callback_data="quota")],
    ])


def kb_menu(kind):
    keys = SCHOOL if kind == "school" else UNI
    rows, row = [], []
    for k in keys:
        row.append(InlineKeyboardButton(TOOLS[k]["title"], callback_data=f"tool:{k}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def kb_back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="menu:home")]])


def kb_cancel():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]])


def kb_run(label):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="run")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")],
    ])


def limit_text():
    return f"⛔ وصلت إلى الحد اليومي ({DAILY_LIMIT} عمليات). يتجدد رصيدك غداً.\nالأدوات المجانية (الحاسبة، المعدل، QR) ما زالت متاحة."


def quota_text(uid):
    return f"📊 المتبقي لك اليوم: {remaining(uid)} من {DAILY_LIMIT} عمليات."


# ───────────────────────── إدارة الحالة ─────────────────────────
def reset_state(context):
    d = context.user_data.get("dir")
    if d:
        shutil.rmtree(d, ignore_errors=True)
    context.user_data.clear()


async def send_result(msg, typ, val):
    if typ == "text":
        for i in range(0, len(val), 4000):
            await msg.reply_text(val[i:i + 4000])
    elif typ == "file":
        with open(val, "rb") as f:
            await msg.reply_document(f, filename=Path(val).name)
    elif typ == "audio":
        with open(val, "rb") as f:
            await msg.reply_audio(f, filename=Path(val).name)
    elif typ == "photo":
        with open(val, "rb") as f:
            await msg.reply_photo(f)


async def execute(msg, uid, context, extra=None):
    ud = context.user_data
    key = ud.get("tool")
    if not key:
        await msg.reply_text("اختر أداة من القائمة أولاً 👇", reply_markup=kb_home())
        return
    tool = TOOLS[key]
    if ud.get("busy"):
        await msg.reply_text("⏳ الطلب السابق ما زال قيد المعالجة...")
        return
    if tool["counted"] and remaining(uid) <= 0:
        await msg.reply_text(limit_text(), reply_markup=kb_back())
        reset_state(context)
        return
    if tool["mode"] == "multi" and not ud.get("files"):
        await msg.reply_text("لم ترسل أي ملف بعد.")
        return

    ud["busy"] = True
    status = await msg.reply_text("⏳ جارٍ المعالجة، انتظر قليلاً...")
    ok, fatal = False, False
    try:
        files = [Path(p) for p in ud.get("files", [])]
        results = await asyncio.to_thread(tool["fn"], files, Path(ud["dir"]), extra)
        for typ, val in results:
            await send_result(msg, typ, val)
        ok = True
    except UserError as e:
        await msg.reply_text(f"⚠️ {e}")
    except Exception:
        log.exception("tool %s failed", key)
        fatal = True
        await msg.reply_text("❌ حدث خطأ أثناء المعالجة. تأكد من الملف وحاول مرة أخرى.")
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
            await msg.reply_text(f"✅ تم!{tail}\nأرسل نصاً آخر أو ارجع للقائمة.", reply_markup=kb_back())
        else:
            reset_state(context)
            await msg.reply_text(f"✅ تم!{tail}", reply_markup=kb_back())
    elif fatal:
        reset_state(context)
        await msg.reply_text("اختر أداة من جديد:", reply_markup=kb_home())


# ───────────────────────── المعالجات ─────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)
    await update.message.reply_text(
        "أهلاً بك في بوت الطالب الشامل 📚\n"
        f"لكل طالب {DAILY_LIMIT} عمليات تحويل يومياً، والحاسبات مجانية بلا حد.\n\n"
        "اختر قسمك:",
        reply_markup=kb_home(),
    )


async def quota_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(quota_text(update.effective_user.id), reply_markup=kb_back())


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)
    await update.message.reply_text("تم الإلغاء.", reply_markup=kb_home())


async def on_button(update: Update, context: ContextTypes.DEFAULT_