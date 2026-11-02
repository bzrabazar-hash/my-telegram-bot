# -*- coding: utf-8 -*-
# Tool functions. Each one: fn(files, workdir, extra, lang) -> [("file"|"text"|"audio"|"photo", value), ...]
# Light on memory: only Pillow + pypdf are needed for most tools; the rest use free web services.
import ast
import base64
import difflib
import io
import json
import math
import operator
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from i18n import tr

DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬۰۱۲۳۴۵۶۷۸۹", "0123456789.,0123456789")
TZ = timezone(timedelta(hours=int(os.environ.get("TZ_OFFSET", "2") or 2)))
HERE = Path(__file__).resolve().parent
FONT_PATH = os.environ.get("FONT_PATH") or str(HERE / "font.ttf")
OCR_API_KEY = os.environ.get("OCR_API_KEY", "").strip()
MYMEMORY_EMAIL = os.environ.get("MYMEMORY_EMAIL", "").strip()
UA = {"User-Agent": "StudentBot/2.0"}


class UserError(Exception):
    """Error shown to the user; `key` is an i18n key."""

    def __init__(self, key, **kw):
        super().__init__(key)
        self.key = key
        self.kw = kw


def has_arabic(s):
    return bool(re.search(r"[\u0600-\u06FF]", s or ""))


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


def http_json(url, data=None, timeout=25):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# ═════════════════════ images ═════════════════════
def f_img2pdf(files, d, extra, lang):
    from PIL import Image

    imgs = []
    for p in files:
        im = to_rgb(Image.open(p))
        im.thumbnail((2200, 2200))
        imgs.append(im)
    out = d / "images.pdf"
    imgs[0].save(out, save_all=True, append_images=imgs[1:])
    return [("file", out)]


def f_compress(files, d, extra, lang):
    from PIL import Image

    im = to_rgb(Image.open(files[0]))
    im.thumbnail((1600, 1600))
    out = d / f"{clean_stem(files[0])}_small.jpg"
    im.save(out, "JPEG", quality=60, optimize=True)
    a, b = files[0].stat().st_size // 1024, out.stat().st_size // 1024
    return [("file", out), ("text", tr(lang, "r_compress", a=a, b=b))]


def f_imgconv(files, d, extra, lang):
    from PIL import Image

    fmt = (extra or "").strip().lower().lstrip(".")
    fmt = {"jpeg": "jpg"}.get(fmt, fmt)
    if fmt not in ("jpg", "png", "webp", "pdf"):
        raise UserError("e_fmt")
    im = Image.open(files[0])
    out = d / f"{clean_stem(files[0])}.{fmt}"
    if fmt in ("jpg", "pdf"):
        to_rgb(im).save(out, "JPEG" if fmt == "jpg" else "PDF")
    else:
        im.convert("RGBA").save(out, fmt.upper())
    return [("file", out)]


def _ocr_request(path, lang_code):
    if not OCR_API_KEY:
        raise UserError("e_ocr_nokey")
    from PIL import Image

    im = to_rgb(Image.open(path))
    im.thumbnail((2000, 2000))
    q = 85
    while True:
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q)
        if buf.tell() < 900_000 or q <= 35:
            break
        q -= 10
        if q < 55:
            im.thumbnail((int(im.width * 0.8), int(im.height * 0.8)))
    body = urllib.parse.urlencode({
        "apikey": OCR_API_KEY,
        "language": lang_code,
        "isOverlayRequired": "false",
        "scale": "true",
        "base64Image": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
    }).encode()
    try:
        data = http_json("https://api.ocr.space/parse/image", data=body, timeout=60)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        raise UserError("e_ocr_fail")
    if data.get("IsErroredOnProcessing"):
        raise UserError("e_ocr_fail")
    return "\n".join(r.get("ParsedText", "") for r in data.get("ParsedResults") or []).strip()


def ocr_text(path, langs=("ara",)):
    """Used by the bot and by payment verification. Returns combined text of all languages."""
    parts = []
    for code in langs:
        try:
            parts.append(_ocr_request(path, code))
        except UserError:
            if not parts and code == langs[-1]:
                raise
    return "\n".join(p for p in parts if p)


def f_ocr(files, d, extra, lang):
    text = _ocr_request(files[0], "ara")
    if not text:
        text = _ocr_request(files[0], "eng")
    if not text:
        raise UserError("e_ocr_empty")
    return [("text", text)]


# ═════════════════════ PDF ═════════════════════
def _pdf_pages_text(path):
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise UserError("e_pdf_enc")
    return [(pg.extract_text() or "").strip() for pg in reader.pages]


def f_pdf_text(files, d, extra, lang):
    text = "\n\n".join(t for t in _pdf_pages_text(files[0]) if t).strip()
    if not text:
        raise UserError("e_pdf_scanned")
    if len(text) <= 3500:
        return [("text", text)]
    out = d / f"{clean_stem(files[0])}.txt"
    out.write_text(text, encoding="utf-8")
    return [("file", out)]


def f_merge(files, d, extra, lang):
    from pypdf import PdfWriter

    if len(files) < 2:
        raise UserError("e_merge_min")
    w = PdfWriter()
    for p in files:
        w.append(str(p))
    out = d / "merged.pdf"
    with open(out, "wb") as f:
        w.write(f)
    return [("file", out)]


def parse_pages(s, n):
    s = (s or "").translate(DIGITS)
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
            raise UserError("e_pages_syntax")
        for x in rng:
            if not 1 <= x <= n:
                raise UserError("e_pages_range", p=x, n=n)
            pages.append(x - 1)
    if not pages:
        raise UserError("e_pages_syntax")
    return pages


def f_split(files, d, extra, lang):
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(files[0]))
    pages = parse_pages(extra, len(reader.pages))
    w = PdfWriter()
    for i in pages:
        w.add_page(reader.pages[i])
    out = d / f"{clean_stem(files[0])}_pages.pdf"
    with open(out, "wb") as f:
        w.write(f)
    return [("file", out)]


# ═════════════════════ Word (text-only, no extra libraries) ═════════════════════
_XML_BAD = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _esc(s):
    s = _XML_BAD.sub("", s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_docx(paragraphs, out):
    """paragraphs: list of str, or None for a page break."""
    body = []
    for p in paragraphs:
        if p is None:
            body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
            continue
        rtl = has_arabic(p)
        ppr = "<w:pPr><w:bidi/></w:pPr>" if rtl else ""
        rpr = "<w:rPr><w:rtl/></w:rPr>" if rtl else ""
        body.append(f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{_esc(p)}</w:t></w:r></w:p>')
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f'<w:body>{"".join(body)}<w:sectPr/></w:body></w:document>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
              '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)


def f_pdf2word(files, d, extra, lang):
    pages = _pdf_pages_text(files[0])
    if not any(pages):
        raise UserError("e_pdf_scanned")
    paras = []
    for i, t in enumerate(pages):
        if i:
            paras.append(None)
        paras.extend(line for line in t.splitlines() if line.strip())
    out = d / f"{clean_stem(files[0])}.docx"
    write_docx(paras, out)
    return [("file", out), ("text", tr(lang, "r_pdf2word_note"))]


# ═════════════════════ Office → text → PDF ═════════════════════
def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _read_docx(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    paras = []
    for p in root.iter():
        if _local(p.tag) == "p":
            txt = "".join(
                (n.text or "") if _local(n.tag) == "t" else ("\t" if _local(n.tag) == "tab" else "")
                for n in p.iter())
            paras.append(txt)
    return paras


def _read_pptx(path):
    paras = []
    with zipfile.ZipFile(path) as z:
        names = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                       key=lambda n: int(re.findall(r"\d+", n)[-1]))
        for i, n in enumerate(names, 1):
            if i > 1:
                paras.append(None)
            paras.append(f"— {i} —")
            root = ET.fromstring(z.read(n))
            for p in root.iter():
                if _local(p.tag) == "p":
                    txt = "".join((x.text or "") for x in p.iter() if _local(x.tag) == "t")
                    if txt.strip():
                        paras.append(txt)
    return paras


def _read_xlsx(path):
    paras = []
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")):
                shared.append("".join((t.text or "") for t in si.iter() if _local(t.tag) == "t"))
        sheets = sorted((n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)),
                        key=lambda n: int(re.findall(r"\d+", n)[-1]))
        for si_, n in enumerate(sheets, 1):
            if si_ > 1:
                paras.append(None)
            paras.append(f"— Sheet {si_} —")
            root = ET.fromstring(z.read(n))
            for row in root.iter():
                if _local(row.tag) != "row":
                    continue
                cells = []
                for c in row:
                    if _local(c.tag) != "c":
                        continue
                    t = c.get("t")
                    v = next((x for x in c if _local(x.tag) == "v"), None)
                    if t == "s" and v is not None and v.text and v.text.isdigit() and int(v.text) < len(shared):
                        cells.append(shared[int(v.text)])
                    elif t == "inlineStr":
                        cells.append("".join((x.text or "") for x in c.iter() if _local(x.tag) == "t"))
                    elif v is not None and v.text is not None:
                        cells.append(v.text)
                if any(x.strip() for x in cells):
                    paras.append(" | ".join(cells))
    return paras


def _read_txt(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1256", "latin-1"):
        try:
            return raw.decode(enc).splitlines()
        except UnicodeDecodeError:
            continue
    return []


def office_paragraphs(path):
    ext = Path(path).suffix.lower()
    try:
        if ext == ".docx":
            return _read_docx(path)
        if ext == ".pptx":
            return _read_pptx(path)
        if ext == ".xlsx":
            return _read_xlsx(path)
        if ext == ".txt":
            return _read_txt(path)
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        raise UserError("e_office_unsupported")
    raise UserError("e_office_unsupported")


# ═════════════════════ text → PDF (Pillow, Arabic aware) ═════════════════════
# Arabic letter forms (isolated, final, initial, medial) from Unicode presentation forms B.
_AR = {
    "ء": (0xFE80,), "آ": (0xFE81, 0xFE82), "أ": (0xFE83, 0xFE84), "ؤ": (0xFE85, 0xFE86),
    "إ": (0xFE87, 0xFE88), "ئ": (0xFE89, 0xFE8A, 0xFE8B, 0xFE8C), "ا": (0xFE8D, 0xFE8E),
    "ب": (0xFE8F, 0xFE90, 0xFE91, 0xFE92), "ة": (0xFE93, 0xFE94), "ت": (0xFE95, 0xFE96, 0xFE97, 0xFE98),
    "ث": (0xFE99, 0xFE9A, 0xFE9B, 0xFE9C), "ج": (0xFE9D, 0xFE9E, 0xFE9F, 0xFEA0),
    "ح": (0xFEA1, 0xFEA2, 0xFEA3, 0xFEA4), "خ": (0xFEA5, 0xFEA6, 0xFEA7, 0xFEA8),
    "د": (0xFEA9, 0xFEAA), "ذ": (0xFEAB, 0xFEAC), "ر": (0xFEAD, 0xFEAE), "ز": (0xFEAF, 0xFEB0),
    "س": (0xFEB1, 0xFEB2, 0xFEB3, 0xFEB4), "ش": (0xFEB5, 0xFEB6, 0xFEB7, 0xFEB8),
    "ص": (0xFEB9, 0xFEBA, 0xFEBB, 0xFEBC), "ض": (0xFEBD, 0xFEBE, 0xFEBF, 0xFEC0),
    "ط": (0xFEC1, 0xFEC2, 0xFEC3, 0xFEC4), "ظ": (0xFEC5, 0xFEC6, 0xFEC7, 0xFEC8),
    "ع": (0xFEC9, 0xFECA, 0xFECB, 0xFECC), "غ": (0xFECD, 0xFECE, 0xFECF, 0xFED0),
    "ف": (0xFED1, 0xFED2, 0xFED3, 0xFED4), "ق": (0xFED5, 0xFED6, 0xFED7, 0xFED8),
    "ك": (0xFED9, 0xFEDA, 0xFEDB, 0xFEDC), "ل": (0xFEDD, 0xFEDE, 0xFEDF, 0xFEE0),
    "م": (0xFEE1, 0xFEE2, 0xFEE3, 0xFEE4), "ن": (0xFEE5, 0xFEE6, 0xFEE7, 0xFEE8),
    "ه": (0xFEE9, 0xFEEA, 0xFEEB, 0xFEEC), "و": (0xFEED, 0xFEEE), "ى": (0xFEEF, 0xFEF0),
    "ي": (0xFEF1, 0xFEF2, 0xFEF3, 0xFEF4),
}
_LAM_ALEF = {"ا": (0xFEFB, 0xFEFC), "أ": (0xFEF7, 0xFEF8), "إ": (0xFEF9, 0xFEFA), "آ": (0xFEF5, 0xFEF6)}


def _reshape(s):
    """Join Arabic letters into their connected forms (logical order is kept)."""
    s = re.sub("[\u064B-\u0652\u0640]", "", s)  # drop diacritics and tatweel
    out, i, n = [], 0, len(s)

    def joins_next(ch):  # letter that connects to the following letter
        return ch in _AR and len(_AR[ch]) == 4

    def connectable(ch):
        return ch in _AR and ch != "ء"

    while i < n:
        c = s[i]
        if c not in _AR:
            out.append(c)
            i += 1
            continue
        prev = s[i - 1] if i else ""
        jp = joins_next(prev) and connectable(c)
        if c == "ل" and i + 1 < n and s[i + 1] in _LAM_ALEF:
            iso, fin = _LAM_ALEF[s[i + 1]]
            out.append(chr(fin if jp else iso))
            i += 2
            continue
        nxt = s[i + 1] if i + 1 < n else ""
        jn = joins_next(c) and connectable(nxt)
        f = _AR[c]
        if len(f) == 4:
            cp = f[3] if jp and jn else f[2] if jn else f[1] if jp else f[0]
        elif len(f) == 2:
            cp = f[1] if jp else f[0]
        else:
            cp = f[0]
        out.append(chr(cp))
        i += 1
    return "".join(out)


def _shape(s):
    """Arabic: join letters, then reverse for left-to-right drawing, keeping Latin/digit runs intact."""
    s = _reshape(s)
    rev = s[::-1]
    rev = re.sub(r"[A-Za-z0-9](?:[A-Za-z0-9 .,:/\-_@%+]*[A-Za-z0-9])?", lambda m: m.group(0)[::-1], rev)
    return rev.translate(str.maketrans("()[]{}<>", ")(][}{><"))


def render_text_pdf(paragraphs, out, max_pages=30):
    from PIL import Image, ImageDraw, ImageFont

    if not os.path.exists(FONT_PATH):
        raise UserError("e_font")
    W, H, M, SIZE = 992, 1403, 80, 26  # A4 at ~120 dpi
    font = ImageFont.truetype(FONT_PATH, SIZE)
    line_h = int(SIZE * 1.7)
    max_w = W - 2 * M
    pages, img, draw, y = [], None, None, 0

    def new_page():
        nonlocal img, draw, y
        if img is not None:
            pages.append(img)
        if len(pages) >= max_pages:
            raise UserError("e_too_many_pages")
        img = Image.new("L", (W, H), 255)
        draw = ImageDraw.Draw(img)
        y = M

    def width(s, rtl):
        return draw.textlength(_shape(s) if rtl else s, font=font)

    new_page()
    for para in paragraphs:
        if para is None:
            new_page()
            continue
        rtl = has_arabic(para)
        words, cur, lines = para.split(" "), "", []
        for w in words:
            test = (cur + " " + w).strip() if cur else w
            if cur and width(test, rtl) > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = test
        lines.append(cur)
        for ln in lines:
            if y + line_h > H - M:
                new_page()
            vis = _shape(ln) if rtl else ln
            x = W - M - draw.textlength(vis, font=font) if rtl else M
            draw.text((x, y), vis, font=font, fill=0)
            y += line_h
        y += line_h // 3
    pages.append(img)
    pages[0].save(out, "PDF", save_all=True, append_images=pages[1:], resolution=120)


def f_office2pdf(files, d, extra, lang):
    paras = office_paragraphs(files[0])
    if not any(p for p in paras if p):
        raise UserError("e_office_empty")
    out = d / f"{clean_stem(files[0])}.pdf"
    render_text_pdf(paras, out)
    return [("file", out), ("text", tr(lang, "r_pdf2word_note"))]


def f_text2pdf(files, d, extra, lang):
    text = (extra or "").strip()
    if not text:
        raise UserError("e_text_empty")
    if len(text) > 6000:
        raise UserError("e_text_long", n=6000)
    out = d / "text.pdf"
    render_text_pdf(text.splitlines(), out)
    return [("file", out)]


# ═════════════════════ audio ═════════════════════
def _ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise UserError("e_stt_ffmpeg")


def f_stt(files, d, extra, lang, code):
    exe = _ffmpeg()
    try:
        import speech_recognition as sr
    except Exception:
        raise UserError("e_stt_ffmpeg")
    try:
        subprocess.run(
            [exe, "-y", "-i", str(files[0]), "-vn", "-ar", "16000", "-ac", "1",
             "-f", "segment", "-segment_time", "40", str(d / "chunk_%03d.wav")],
            check=True, capture_output=True, timeout=240)
    except Exception:
        raise UserError("e_stt_read")
    chunks = sorted(d.glob("chunk_*.wav"))
    if not chunks:
        raise UserError("e_stt_read")
    if len(chunks) > 15:
        raise UserError("e_stt_long")
    r = sr.Recognizer()
    parts = []
    for c in chunks:
        with sr.AudioFile(str(c)) as s:
            audio = r.record(s)
        try:
            parts.append(r.recognize_google(audio, language=code))
        except sr.UnknownValueError:
            pass
        except sr.RequestError:
            raise UserError("e_stt_net")
    text = " ".join(parts).strip()
    if not text:
        raise UserError("e_stt_empty")
    return [("text", text)]


def _split_lang_prefix(text, default):
    m = re.match(r"^\s*(ar|en|fr)\s*[:：]\s*(.+)$", text or "", re.S | re.I)
    if m:
        return m.group(1).lower(), m.group(2).strip()
    return default, (text or "").strip()


def f_tts(files, d, extra, lang):
    from gtts import gTTS

    code, text = _split_lang_prefix(extra, "ar" if has_arabic(extra) else "en")
    if not text:
        raise UserError("e_text_empty")
    if len(text) > 1000:
        raise UserError("e_tts_long")
    out = d / "speech.mp3"
    gTTS(text, lang=code).save(str(out))
    return [("audio", out)]


# ═════════════════════ text tools ═════════════════════
def f_translate(files, d, extra, lang):
    text = (extra or "").strip()
    m = re.match(r"^\s*(ar|en|fr)\s*(?:>|->)\s*(ar|en|fr)\s*[:：]\s*(.+)$", text, re.S | re.I)
    if m:
        src, dst, text = m.group(1).lower(), m.group(2).lower(), m.group(3).strip()
    else:
        dst, text = _split_lang_prefix(text, "")
        src = "ar" if has_arabic(text) else "en"
        dst = dst or ("en" if src == "ar" else "ar")
    if not text:
        raise UserError("e_text_empty")
    if len(text) > 300:
        raise UserError("e_text_long", n=300)
    if src == dst:
        src = "en" if dst == "ar" else "ar"
    q = {"q": text, "langpair": f"{src}|{dst}"}
    if MYMEMORY_EMAIL:
        q["de"] = MYMEMORY_EMAIL
    try:
        data = http_json("https://api.mymemory.translated.net/get?" + urllib.parse.urlencode(q))
        out = (data.get("responseData") or {}).get("translatedText", "")
        if data.get("responseStatus") not in (200, "200") or not out:
            raise ValueError
    except Exception:
        raise UserError("e_translate")
    return [("text", f"🌐 {src} → {dst}\n{out}")]


def f_define(files, d, extra, lang):
    word = (extra or "").strip().split()[0:1]
    if not word or not re.match(r"^[A-Za-z'\-]+$", word[0]):
        raise UserError("e_define_none")
    url = "https://api.dictionaryapi.dev/api/v2/entries/en/" + urllib.parse.quote(word[0].lower())
    try:
        data = http_json(url, timeout=20)
    except urllib.error.HTTPError as e:
        raise UserError("e_define_none" if e.code == 404 else "e_define_net")
    except Exception:
        raise UserError("e_define_net")
    if not isinstance(data, list) or not data:
        raise UserError("e_define_none")
    entry = data[0]
    lines = [f"📖 {entry.get('word', word[0])} {entry.get('phonetic', '')}".strip()]
    for mean in (entry.get("meanings") or [])[:3]:
        lines.append(f"\n• {mean.get('partOfSpeech', '')}")
        for df in (mean.get("definitions") or [])[:2]:
            lines.append(f"  - {df.get('definition', '')}")
            if df.get("example"):
                lines.append(f"    “{df['example']}”")
    return [("text", "\n".join(lines))]


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
        ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"sqrt": math.sqrt, "abs": abs, "log": math.log10, "ln": math.log,
          "sin": lambda x: math.sin(math.radians(x)), "cos": lambda x: math.cos(math.radians(x)),
          "tan": lambda x: math.tan(math.radians(x))}
_CONST = {"pi": math.pi, "e": math.e}


def _ev(n):
    if isinstance(n, ast.Expression):
        return _ev(n.body)
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        return n.value
    if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
        a, b = _ev(n.left), _ev(n.right)
        if isinstance(n.op, ast.Pow) and abs(b) > 1000:
            raise UserError("e_calc_pow")
        return _OPS[type(n.op)](a, b)
    if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
        return _OPS[type(n.op)](_ev(n.operand))
    if isinstance(n, ast.Name) and n.id in _CONST:
        return _CONST[n.id]
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and len(n.args) == 1:
        return _FUNCS[n.func.id](_ev(n.args[0]))
    raise UserError("e_calc")


def f_calc(files, d, extra, lang):
    expr = (extra or "").translate(DIGITS).replace("×", "*").replace("÷", "/").replace("^", "**")
    try:
        val = _ev(ast.parse(expr.strip(), mode="eval"))
    except UserError:
        raise
    except ZeroDivisionError:
        raise UserError("e_calc_zero")
    except (SyntaxError, ValueError, OverflowError, TypeError):
        raise UserError("e_calc")
    if isinstance(val, float):
        val = round(val, 10)
        if val.is_integer():
            val = int(val)
    return [("text", f"= {val}")]


def f_gpa(files, d, extra, lang):
    pts_sum = hrs_sum = 0.0
    for line in (extra or "").translate(DIGITS).splitlines():
        nums = re.findall(r"\d+(?:\.\d+)?", line)
        if len(nums) >= 2:
            p, h = float(nums[0]), float(nums[1])
            pts_sum += p * h
            hrs_sum += h
    if hrs_sum == 0:
        raise UserError("e_gpa")
    return [("text", tr(lang, "r_gpa", gpa=pts_sum / hrs_sum, hrs=hrs_sum))]


def f_qr(files, d, extra, lang):
    import qrcode

    text = (extra or "").strip()
    if not text:
        raise UserError("e_text_empty")
    out = d / "qr.png"
    qrcode.make(text).save(out)
    return [("photo", out)]


# ── units ──
_UNITS = {
    "length": {"m": 1, "km": 1000, "cm": 0.01, "mm": 0.001, "mi": 1609.344, "yd": 0.9144, "ft": 0.3048, "in": 0.0254},
    "mass": {"kg": 1, "g": 0.001, "mg": 1e-6, "t": 1000, "lb": 0.45359237, "oz": 0.028349523125},
    "time": {"s": 1, "min": 60, "h": 3600, "day": 86400, "week": 604800},
    "volume": {"l": 1, "ml": 0.001, "m3": 1000, "gal": 3.785411784, "cup": 0.2365882365},
    "area": {"m2": 1, "km2": 1e6, "cm2": 1e-4, "ha": 1e4, "ft2": 0.09290304, "acre": 4046.8564224},
    "speed": {"m/s": 1, "km/h": 1 / 3.6, "mph": 0.44704, "kn": 0.514444},
    "temp": {"c": None, "f": None, "k": None},
}
_ALIAS = {
    "meter": "m", "metre": "m", "متر": "m", "م": "m", "kilometer": "km", "كم": "km", "كيلومتر": "km",
    "سم": "cm", "سنتيمتر": "cm", "ملم": "mm", "مم": "mm", "ميل": "mi", "mile": "mi", "miles": "mi",
    "yard": "yd", "foot": "ft", "feet": "ft", "inch": "in", "inches": "in", "بوصة": "in", "قدم": "ft",
    "كجم": "kg", "كغ": "kg", "كيلو": "kg", "جم": "g", "غرام": "g", "جرام": "g", "gram": "g", "ton": "t", "طن": "t",
    "pound": "lb", "lbs": "lb", "رطل": "lb", "ounce": "oz", "اونصة": "oz",
    "sec": "s", "second": "s", "ثانية": "s", "دقيقة": "min", "minute": "min", "minutes": "min",
    "hour": "h", "hr": "h", "ساعة": "h", "hours": "h", "يوم": "day", "days": "day", "day": "day", "أسبوع": "week", "weeks": "week",
    "liter": "l", "litre": "l", "لتر": "l", "مل": "ml", "gallon": "gal", "جالون": "gal", "كوب": "cup",
    "هكتار": "ha", "فدان": "acre", "ft²": "ft2", "m²": "m2", "km²": "km2", "cm²": "cm2", "m³": "m3",
    "kph": "km/h", "kmh": "km/h", "ms": "m/s", "عقدة": "kn",
    "celsius": "c", "°c": "c", "مئوية": "c", "fahrenheit": "f", "°f": "f", "فهرنهايت": "f", "kelvin": "k", "كلفن": "k",
}


def _unit(u):
    u = u.strip().lower().rstrip(".")
    u = _ALIAS.get(u, u)
    for cat, table in _UNITS.items():
        if u in table:
            return cat, u
    raise UserError("e_units_unknown", u=u)


def _temp(v, a, b):
    k = {"c": v + 273.15, "f": (v - 32) * 5 / 9 + 273.15, "k": v}[a]
    return {"c": k - 273.15, "f": (k - 273.15) * 9 / 5 + 32, "k": k}[b]


def f_units(files, d, extra, lang):
    t = (extra or "").translate(DIGITS).strip()
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*(.+)$", t)
    if not m:
        raise UserError("e_units")
    val = float(m.group(1))
    rest = re.sub(r"\b(to|in|into)\b|->|→|=|إلى|الى|في", " ", m.group(2), flags=re.I).split()
    if len(rest) != 2:
        raise UserError("e_units")
    (ca, a), (cb, b) = _unit(rest[0]), _unit(rest[1])
    if ca != cb:
        raise UserError("e_units_incompat")
    res = _temp(val, a, b) if ca == "temp" else val * _UNITS[ca][a] / _UNITS[cb][b]
    return [("text", f"{val:g} {a} = {res:.10g} {b}")]


def f_quad(files, d, extra, lang):
    nums = re.findall(r"-?\d+(?:\.\d+)?", (extra or "").translate(DIGITS))
    if len(nums) != 3:
        raise UserError("e_quad")
    a, b, c = map(float, nums)
    if a == 0:
        if b == 0:
            return [("text", tr(lang, "r_quad_degenerate"))]
        return [("text", tr(lang, "r_quad_linear", x1=f"{-c / b:.10g}"))]
    disc = b * b - 4 * a * c
    if disc > 0:
        s = math.sqrt(disc)
        return [("text", tr(lang, "r_quad_two", x1=f"{(-b + s) / (2 * a):.10g}", x2=f"{(-b - s) / (2 * a):.10g}", d=f"{disc:.10g}"))]
    if disc == 0:
        return [("text", tr(lang, "r_quad_one", x1=f"{-b / (2 * a):.10g}"))]
    re_, im_ = -b / (2 * a), math.sqrt(-disc) / (2 * a)
    return [("text", tr(lang, "r_quad_none", d=f"{disc:.10g}", x1=f"{re_:.6g} + {abs(im_):.6g}i", x2=f"{re_:.6g} - {abs(im_):.6g}i"))]


def _factors(n):
    out, p = [], 2
    while p * p <= n and p < 2_000_000:
        while n % p == 0:
            out.append(p)
            n //= p
        p += 1 if p == 2 else 2
    if n > 1:
        out.append(n)
    return out


def f_nums(files, d, extra, lang):
    try:
        nums = [int(x) for x in re.findall(r"\d+", (extra or "").translate(DIGITS))]
    except ValueError:
        nums = []
    if len(nums) < 2 or any(n <= 0 or n > 10**12 for n in nums) or len(nums) > 10:
        raise UserError("e_nums")
    g, l = nums[0], nums[0]
    for n in nums[1:]:
        g = math.gcd(g, n)
        l = l * n // math.gcd(l, n)
    fl = []
    for n in nums:
        fs = _factors(n)
        if len(fs) <= 1:
            fl.append(f"{n} = {n}")
        else:
            cnt = {}
            for p in fs:
                cnt[p] = cnt.get(p, 0) + 1
            fl.append(f"{n} = " + " × ".join(f"{p}^{e}" if e > 1 else str(p) for p, e in cnt.items()))
    return [("text", tr(lang, "r_nums", g=g, l=l, f="\n".join(fl)))]


def f_wordcount(files, d, extra, lang):
    t = (extra or "").strip()
    if not t:
        raise UserError("e_text_empty")
    w = len(t.split())
    s = len([x for x in re.split(r"[.!?؟…]+", t) if x.strip()])
    p = len([x for x in re.split(r"\n\s*\n|\n", t) if x.strip()])
    return [("text", tr(lang, "r_wordcount", w=w, c=len(t), c2=len(re.sub(r"\s", "", t)), s=s, p=p, m=max(1, round(w / 200))))]


def f_summarize(files, d, extra, lang):
    t = (extra or "").strip()
    sents = [x.strip() for x in re.split(r"(?<=[.!?؟…])\s+|\n+", t) if len(x.strip()) > 15]
    if len(sents) < 4:
        raise UserError("e_sum_short")
    norm = lambda s: re.sub(r"[\u064B-\u0652\u0640]", "", s.lower())
    words = lambda s: [w for w in re.findall(r"\w+", norm(s)) if len(w) > 2]
    freq = {}
    for s in sents:
        for w in words(s):
            freq[w] = freq.get(w, 0) + 1
    scored = []
    for i, s in enumerate(sents):
        ws = words(s)
        scored.append((sum(freq[w] for w in ws) / (len(ws) ** 0.7 + 1), i))
    k = min(6, max(2, len(sents) // 4))
    keep = sorted(i for _, i in sorted(scored, reverse=True)[:k])
    return [("text", tr(lang, "r_summary", t="\n\n".join(sents[i] for i in keep)))]


def f_cite(files, d, extra, lang):
    parts = [p.strip() for p in (extra or "").split("|")]
    if len(parts) < 4 or not all(parts[:4]):
        raise UserError("e_cite")
    author, title, year, pub = parts[:4]
    cite = f"{author if author.endswith('.') else author + '.'} ({year}). {title}. {pub}."
    if len(parts) > 4 and parts[4]:
        cite += f" {parts[4]}"
    return [("text", cite)]


def f_countdown(files, d, extra, lang):
    t = (extra or "").translate(DIGITS).strip().replace("/", "-")
    try:
        target = datetime.strptime(t, "%Y-%m-%d").date()
    except ValueError:
        raise UserError("e_date")
    days = (target - datetime.now(TZ).date()).days
    if days < 0:
        return [("text", tr(lang, "r_countdown_past"))]
    if days == 0:
        return [("text", tr(lang, "r_countdown_today"))]
    return [("text", tr(lang, "r_countdown", date=target.isoformat(), d=days, w=round(days / 7, 1)))]


# ═════════════════════ payment receipt check ═════════════════════
def _alnum(s):
    return re.sub(r"[^0-9a-z]", "", (s or "").translate(DIGITS).lower())


def check_receipt(text, txn, amount, account, name):
    """Returns (ok, reason_key). reason_key in why_txn / why_amount / why_recipient."""
    t = (text or "").translate(DIGITS)
    if _alnum(txn) not in _alnum(t):
        return False, "why_txn"
    found_amount = False
    for m in re.finditer(r"\d[\d,،.]*", t):
        raw = m.group(0).replace(",", "").replace("،", "").rstrip(".")
        try:
            if abs(float(raw) - float(amount)) < 0.01:
                found_amount = True
                break
        except ValueError:
            continue
    if not found_amount:
        return False, "why_amount"
    acc = re.sub(r"\D", "", account or "")
    name_tokens = [w for w in re.split(r"\s+", (name or "").strip()) if len(w) >= 3]
    if acc or name_tokens:
        digits = re.sub(r"\D", "", t)
        acc_ok = bool(acc) and (acc in digits or acc[-6:] in digits)
        words = re.findall(r"\w+", t.lower())
        hits = sum(1 for tok in name_tokens
                   if difflib.get_close_matches(tok.lower(), words, n=1, cutoff=0.78))
        name_ok = bool(name_tokens) and hits >= math.ceil(len(name_tokens) / 2)
        if not (acc_ok or name_ok):
            return False, "why_recipient"
    return True, ""
