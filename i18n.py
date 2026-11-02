# -*- coding: utf-8 -*-
# All user-facing text, in three languages. To add a language: add its code to LANGS
# and a value for it in every entry (missing entries fall back to Arabic).

LANGS = {"ar": "العربية", "en": "English", "fr": "Français"}
DEFAULT_LANG = "ar"

S = {}


def _a(key, ar, en, fr):
    S[key] = {"ar": ar, "en": en, "fr": fr}


def tr(lang, key, **kw):
    d = S.get(key)
    if not d:
        return key
    text = d.get(lang) or d["ar"]
    return text.format(**kw) if kw else text


# ───────────── core UI ─────────────
_a("choose_lang", "🌐 اختر اللغة\nChoose your language\nChoisissez la langue",
   "🌐 اختر اللغة\nChoose your language\nChoisissez la langue",
   "🌐 اختر اللغة\nChoose your language\nChoisissez la langue")
_a("lang_set", "✅ تم تغيير اللغة إلى العربية.", "✅ Language set to English.", "✅ Langue réglée sur le français.")
_a("welcome",
   "أهلاً بك في بوت الطالب الشامل 📚\nلكل طالب {limit} عمليات تحويل يومياً، والأدوات الحسابية والنصية مجانية بلا حد.\n\nاختر قسمك:",
   "Welcome to the All-in-One Student Bot 📚\nEvery student gets {limit} file operations per day. Calculators and text tools are free and unlimited.\n\nChoose your section:",
   "Bienvenue sur le bot tout-en-un de l'étudiant 📚\nChaque étudiant a {limit} opérations de fichiers par jour. Les calculatrices et outils de texte sont gratuits et illimités.\n\nChoisissez votre section :")
_a("pick_section", "اختر قسمك:", "Choose your section:", "Choisissez votre section :")
_a("btn_school", "🎒 طالب مدرسي", "🎒 School student", "🎒 Élève")
_a("btn_uni", "🎓 طالب جامعي", "🎓 University student", "🎓 Étudiant")
_a("btn_quota", "📊 رصيدي اليوم", "📊 My quota today", "📊 Mon quota du jour")
_a("btn_lang", "🌐 اللغة", "🌐 Language", "🌐 Langue")
_a("btn_pay", "💳 يوم مفتوح (غير محدود)", "💳 Unlimited day pass", "💳 Pass illimité (1 jour)")
_a("btn_pay_buy", "💳 شراء يوم مفتوح", "💳 Buy a day pass", "💳 Acheter un pass")
_a("btn_home", "🏠 القائمة الرئيسية", "🏠 Main menu", "🏠 Menu principal")
_a("btn_cancel", "❌ إلغاء", "❌ Cancel", "❌ Annuler")
_a("title_school", "🎒 أدوات الطالب المدرسي", "🎒 School tools", "🎒 Outils scolaires")
_a("title_uni", "🎓 أدوات الطالب الجامعي", "🎓 University tools", "🎓 Outils universitaires")
_a("pick_tool_first", "اختر أداة من القائمة أولاً 👇", "Pick a tool from the menu first 👇", "Choisissez d'abord un outil dans le menu 👇")
_a("pick_tool_again", "اختر أداة من جديد:", "Pick a tool again:", "Choisissez un outil :")
_a("cancelled", "تم الإلغاء.", "Cancelled.", "Annulé.")
_a("busy", "⏳ الطلب السابق ما زال قيد المعالجة...", "⏳ The previous request is still processing...", "⏳ La demande précédente est en cours...")
_a("processing", "⏳ جارٍ المعالجة، انتظر قليلاً...", "⏳ Processing, please wait...", "⏳ Traitement en cours, patientez...")
_a("done", "✅ تم!", "✅ Done!", "✅ Terminé !")
_a("more_or_menu", "أرسل نصاً آخر أو ارجع للقائمة.", "Send more text or go back to the menu.", "Envoyez un autre texte ou revenez au menu.")
_a("quota_left", "📊 المتبقي لك اليوم: {n} من {limit} عمليات.", "📊 Left today: {n} of {limit} operations.", "📊 Restant aujourd'hui : {n} sur {limit} opérations.")
_a("quota_pass", "✅ يومك المفتوح ساري حتى {until} (استخدام غير محدود).", "✅ Your day pass is active until {until} (unlimited).", "✅ Votre pass est actif jusqu'à {until} (illimité).")
_a("limit", "⛔ وصلت إلى الحد اليومي ({limit} عمليات). يتجدد رصيدك غداً.\nالأدوات المجانية (الحاسبة وغيرها) ما زالت متاحة.",
   "⛔ You reached the daily limit ({limit} operations). It resets tomorrow.\nFree tools (calculator and others) are still available.",
   "⛔ Limite quotidienne atteinte ({limit} opérations). Elle se renouvelle demain.\nLes outils gratuits (calculatrice, etc.) restent disponibles.")
_a("limit_pay", "\n\n💳 أو اشترِ «يوماً مفتوحاً» بلا حد لمدة {hours} ساعة.",
   "\n\n💳 Or buy a day pass: unlimited for {hours} hours.",
   "\n\n💳 Ou achetez un pass : illimité pendant {hours} h.")
_a("k_image", "صورة", "an image", "une image")
_a("k_pdf", "ملف PDF", "a PDF file", "un fichier PDF")
_a("k_office", "ملف Word / PowerPoint / Excel / نص", "a Word / PowerPoint / Excel / text file", "un fichier Word / PowerPoint / Excel / texte")
_a("k_audio", "ملف صوتي أو رسالة صوتية", "an audio file or voice message", "un fichier audio ou message vocal")
_a("wrong_type", "⚠️ نوع الملف غير مناسب. المطلوب: {need}", "⚠️ Wrong file type. Needed: {need}", "⚠️ Type de fichier incorrect. Attendu : {need}")
_a("too_big", "⚠️ الملف كبير. الحد الأقصى {mb} ميغابايت.", "⚠️ File too large. Maximum {mb} MB.", "⚠️ Fichier trop volumineux. Maximum {mb} Mo.")
_a("max_files", "⚠️ الحد الأقصى 20 ملفاً في الطلب الواحد.", "⚠️ Maximum 20 files per request.", "⚠️ Maximum 20 fichiers par demande.")
_a("dl_fail", "❌ تعذر تنزيل الملف، حاول مرة أخرى.", "❌ Could not download the file, try again.", "❌ Téléchargement impossible, réessayez.")
_a("got_files", "📥 استلمت {n} ملف. أرسل المزيد أو اضغط الزر.", "📥 Received {n} file(s). Send more or press the button.", "📥 {n} fichier(s) reçu(s). Envoyez-en d'autres ou appuyez sur le bouton.")
_a("no_files", "لم ترسل أي ملف بعد.", "You haven't sent any file yet.", "Vous n'avez encore envoyé aucun fichier.")
_a("send_file_first", "أرسل الملف أولاً.", "Send the file first.", "Envoyez d'abord le fichier.")
_a("text_only", "هذه الأداة تستقبل نصاً فقط، أرسل نصاً.", "This tool only takes text. Send text.", "Cet outil n'accepte que du texte.")
_a("file_only", "هذه الأداة تحتاج ملفاً، وليس نصاً. أرسل الملف المطلوب.", "This tool needs a file, not text. Send the file.", "Cet outil nécessite un fichier, pas du texte.")
_a("err_generic", "❌ حدث خطأ أثناء المعالجة. تأكد من الملف وحاول مرة أخرى.", "❌ Something went wrong. Check the file and try again.", "❌ Une erreur est survenue. Vérifiez le fichier et réessayez.")
_a("btn_run_pdf", "✅ إنشاء PDF", "✅ Create PDF", "✅ Créer le PDF")
_a("btn_run_merge", "✅ دمج", "✅ Merge", "✅ Fusionner")

# ───────────── tool titles ─────────────
_a("t_img2pdf", "📷 صور ← PDF", "📷 Images → PDF", "📷 Images → PDF")
_a("t_compress", "🗜 ضغط صورة", "🗜 Compress image", "🗜 Compresser image")
_a("t_imgconv", "🖼 تحويل صيغة صورة", "🖼 Convert image format", "🖼 Convertir image")
_a("t_ocr", "🔍 صورة ← نص", "🔍 Image → text (OCR)", "🔍 Image → texte (OCR)")
_a("t_pdf_text", "📄 PDF ← نص", "📄 PDF → text", "📄 PDF → texte")
_a("t_pdf2word", "📝 PDF ← Word", "📝 PDF → Word", "📝 PDF → Word")
_a("t_office2pdf", "📑 Word/PPT/Excel ← PDF", "📑 Word/PPT/Excel → PDF", "📑 Word/PPT/Excel → PDF")
_a("t_merge", "🧷 دمج PDF", "🧷 Merge PDFs", "🧷 Fusionner PDF")
_a("t_split", "✂️ استخراج صفحات PDF", "✂️ Extract PDF pages", "✂️ Extraire des pages PDF")
_a("t_stt_ar", "🎙 صوت ← نص (عربي)", "🎙 Speech → text (Arabic)", "🎙 Voix → texte (arabe)")
_a("t_stt_en", "🎙 صوت ← نص (English)", "🎙 Speech → text (English)", "🎙 Voix → texte (anglais)")
_a("t_tts", "🔊 نص ← صوت", "🔊 Text → speech", "🔊 Texte → voix")
_a("t_text2pdf", "🧾 نص ← PDF", "🧾 Text → PDF", "🧾 Texte → PDF")
_a("t_translate", "🌐 ترجمة", "🌐 Translate", "🌐 Traduire")
_a("t_define", "📖 قاموس إنجليزي", "📖 English dictionary", "📖 Dictionnaire anglais")
_a("t_calc", "🧮 حاسبة علمية", "🧮 Scientific calculator", "🧮 Calculatrice scientifique")
_a("t_gpa", "🎓 حاسبة المعدل", "🎓 GPA calculator", "🎓 Calcul de moyenne")
_a("t_qr", "🔳 إنشاء QR", "🔳 Make a QR code", "🔳 Créer un QR code")
_a("t_units", "📏 محول الوحدات", "📏 Unit converter", "📏 Convertisseur d'unités")
_a("t_quad", "📐 معادلة تربيعية", "📐 Quadratic equation", "📐 Équation du 2nd degré")
_a("t_nums", "🔢 القاسم والمضاعف", "🔢 GCD / LCM / factors", "🔢 PGCD / PPCM / facteurs")
_a("t_wordcount", "🔤 عدّاد الكلمات", "🔤 Word counter", "🔤 Compteur de mots")
_a("t_summarize", "📝 تلخيص نص", "📝 Summarize text", "📝 Résumer un texte")
_a("t_cite", "📚 مولّد مراجع APA", "📚 APA citation maker", "📚 Générateur de citation APA")
_a("t_countdown", "⏳ عدّ تنازلي للامتحان", "⏳ Exam countdown", "⏳ Compte à rebours examen")
_a("t_timer", "⏱ مؤقت مذاكرة", "⏱ Study timer", "⏱ Minuteur d'étude")

# ───────────── tool prompts ─────────────
_a("p_img2pdf", "أرسل الصور (واحدة تلو الأخرى) ثم اضغط «إنشاء PDF».", "Send the images one by one, then press “Create PDF”.", "Envoyez les images une par une, puis appuyez sur « Créer le PDF ».")
_a("p_compress", "أرسل الصورة التي تريد تصغير حجمها.", "Send the image you want to shrink.", "Envoyez l'image à réduire.")
_a("p_imgconv", "أرسل الصورة.", "Send the image.", "Envoyez l'image.")
_a("a_imgconv", "اكتب الصيغة المطلوبة: jpg أو png أو webp أو pdf", "Type the target format: jpg, png, webp or pdf", "Écrivez le format voulu : jpg, png, webp ou pdf")
_a("p_ocr", "أرسل صورة فيها نص (كتاب، سبورة، ملاحظات) لاستخراج النص.\nيدعم العربية والإنجليزية.", "Send a photo that contains text (book, board, notes) to extract it.\nArabic and English are supported.", "Envoyez une photo contenant du texte (livre, tableau, notes).\nArabe et anglais pris en charge.")
_a("p_pdf_text", "أرسل ملف PDF لاستخراج نصه.", "Send a PDF to extract its text.", "Envoyez un PDF pour en extraire le texte.")
_a("p_pdf2word", "أرسل ملف PDF لتحويل نصه إلى Word.\nℹ️ التحويل نصي: يحافظ على النص دون الصور والتنسيق.", "Send a PDF to convert its text to Word.\nℹ️ Text-only: images and layout are not kept.", "Envoyez un PDF pour convertir son texte en Word.\nℹ️ Texte seulement : images et mise en page non conservées.")
_a("p_office2pdf", "أرسل ملف Word (docx) أو PowerPoint (pptx) أو Excel (xlsx) أو txt.\nℹ️ التحويل نصي: يحافظ على النص دون الصور والتنسيق.", "Send a Word (docx), PowerPoint (pptx), Excel (xlsx) or txt file.\nℹ️ Text-only: images and layout are not kept.", "Envoyez un fichier Word (docx), PowerPoint (pptx), Excel (xlsx) ou txt.\nℹ️ Texte seulement : images et mise en page non conservées.")
_a("p_merge", "أرسل ملفات PDF بالترتيب المطلوب ثم اضغط «دمج».", "Send the PDFs in order, then press “Merge”.", "Envoyez les PDF dans l'ordre, puis appuyez sur « Fusionner ».")
_a("p_split", "أرسل ملف PDF.", "Send the PDF.", "Envoyez le PDF.")
_a("a_split", "أرسل أرقام الصفحات المطلوبة. مثال: 1-3 أو 2,5,7-9", "Send the page numbers you want. Example: 1-3 or 2,5,7-9", "Envoyez les numéros de pages. Exemple : 1-3 ou 2,5,7-9")
_a("p_stt_ar", "أرسل رسالة صوتية أو ملفاً صوتياً (عربي).", "Send a voice message or audio file (Arabic).", "Envoyez un message vocal ou fichier audio (arabe).")
_a("p_stt_en", "أرسل رسالة صوتية أو ملفاً صوتياً (إنجليزي).", "Send a voice message or audio file (English).", "Envoyez un message vocal ou fichier audio (anglais).")
_a("p_tts", "أرسل النص الذي تريد سماعه.\nيمكنك البدء بـ ar: أو en: أو fr: لاختيار اللغة.", "Send the text you want to hear.\nStart with ar: en: or fr: to choose the language.", "Envoyez le texte à écouter.\nCommencez par ar: en: ou fr: pour choisir la langue.")
_a("p_text2pdf", "أرسل النص (حتى 6000 حرف) وسأحوّله إلى ملف PDF.", "Send the text (up to 6000 characters) and I'll make a PDF.", "Envoyez le texte (jusqu'à 6000 caractères) pour obtenir un PDF.")
_a("p_translate", "أرسل النص (حتى 300 حرف). عربي ← إنجليزي، وغيره ← عربي تلقائياً.\nلاختيار لغة الهدف ابدأ بـ en: أو fr: أو ar:\nمثال: fr: كيف حالك؟", "Send text (up to 300 characters). Arabic → English, anything else → Arabic by default.\nTo pick the target start with en: fr: or ar:\nExample: fr: How are you?", "Envoyez un texte (300 caractères max). Arabe → anglais, sinon → arabe par défaut.\nPour choisir la cible, commencez par en: fr: ou ar:\nExemple : ar: Comment ça va ?")
_a("p_define", "اكتب كلمة إنجليزية لأعرض معناها. (مجاني)", "Type an English word to see its meaning. (free)", "Écrivez un mot anglais pour voir sa définition. (gratuit)")
_a("p_calc", "أرسل العملية. أمثلة: (5+3)*2^3 ، sqrt(144) ، sin(30) ، log(1000)\n(مجانية بلا حد)", "Send an expression. Examples: (5+3)*2^3, sqrt(144), sin(30), log(1000)\n(free, unlimited)", "Envoyez une expression. Exemples : (5+3)*2^3, sqrt(144), sin(30), log(1000)\n(gratuit, illimité)")
_a("p_gpa", "اكتب كل مادة في سطر: النقاط ثم الساعات.\nمثال:\n4 3\n3.5 2\n3 4\n(مجانية بلا حد)", "Write one course per line: points then credit hours.\nExample:\n4 3\n3.5 2\n3 4\n(free, unlimited)", "Une matière par ligne : points puis crédits.\nExemple :\n4 3\n3.5 2\n3 4\n(gratuit, illimité)")
_a("p_qr", "أرسل النص أو الرابط لإنشاء رمز QR. (مجاني بلا حد)", "Send text or a link to make a QR code. (free, unlimited)", "Envoyez un texte ou un lien pour créer un QR code. (gratuit)")
_a("p_units", "اكتب التحويل بهذه الصيغة:\n10 km to m\n30 c to f\n2 kg to lb\n5 ساعة to min\n(طول، كتلة، وقت، حجم، مساحة، سرعة، حرارة)", "Write the conversion like this:\n10 km to m\n30 c to f\n2 kg to lb\n5 h to min\n(length, mass, time, volume, area, speed, temperature)", "Écrivez la conversion ainsi :\n10 km to m\n30 c to f\n2 kg to lb\n5 h to min\n(longueur, masse, temps, volume, surface, vitesse, température)")
_a("p_quad", "أرسل ثلاثة أرقام a b c لحل المعادلة ax²+bx+c=0\nمثال: 1 -5 6", "Send three numbers a b c to solve ax²+bx+c=0\nExample: 1 -5 6", "Envoyez trois nombres a b c pour résoudre ax²+bx+c=0\nExemple : 1 -5 6")
_a("p_nums", "أرسل رقمين أو أكثر مفصولة بمسافة.\nمثال: 12 18", "Send two or more numbers separated by spaces.\nExample: 12 18", "Envoyez deux nombres ou plus séparés par des espaces.\nExemple : 12 18")
_a("p_wordcount", "أرسل النص لأعدّ كلماته وجمله.", "Send text to count its words and sentences.", "Envoyez un texte pour compter mots et phrases.")
_a("p_summarize", "أرسل نصاً طويلاً (4 جمل على الأقل) وسأستخرج أهم جمله.", "Send a longer text (at least 4 sentences) and I'll pick the key sentences.", "Envoyez un texte plus long (4 phrases min.) et j'en extrairai l'essentiel.")
_a("p_cite", "اكتب بيانات المرجع بهذه الصيغة:\nالمؤلف | العنوان | السنة | الناشر أو الموقع | الرابط (اختياري)", "Write the source like this:\nAuthor | Title | Year | Publisher or site | URL (optional)", "Écrivez la source ainsi :\nAuteur | Titre | Année | Éditeur ou site | URL (facultatif)")
_a("p_countdown", "اكتب تاريخ الامتحان بالصيغة YYYY-MM-DD\nمثال: 2026-12-20", "Type the exam date as YYYY-MM-DD\nExample: 2026-12-20", "Écrivez la date de l'examen : AAAA-MM-JJ\nExemple : 2026-12-20")
_a("p_timer", "أرسل عدد دقائق المذاكرة (من 1 إلى 180) وسأنبهك عند انتهاء الوقت.", "Send the number of study minutes (1 to 180) and I'll ping you when time is up.", "Envoyez le nombre de minutes d'étude (1 à 180) et je vous préviendrai.")

# ───────────── errors raised by tools ─────────────
_a("e_ocr_nokey", "خدمة قراءة النصوص غير مفعّلة بعد على الخادم.", "The OCR service is not enabled on the server yet.", "Le service OCR n'est pas encore activé sur le serveur.")
_a("e_ocr_empty", "لم أجد نصاً واضحاً في الصورة. جرّب صورة أوضح وبإضاءة جيدة.", "I couldn't find clear text in the image. Try a sharper, well-lit photo.", "Aucun texte clair trouvé. Essayez une photo plus nette et bien éclairée.")
_a("e_ocr_fail", "تعذر الاتصال بخدمة قراءة النصوص. حاول لاحقاً.", "Could not reach the OCR service. Try later.", "Service OCR injoignable. Réessayez plus tard.")
_a("e_pdf_enc", "الملف محمي بكلمة مرور.", "The file is password-protected.", "Le fichier est protégé par mot de passe.")
_a("e_pdf_scanned", "الملف لا يحتوي نصاً (غالباً ممسوح ضوئياً). صوّر صفحاته واستخدم أداة «صورة ← نص».", "The PDF has no text (probably scanned). Photograph its pages and use “Image → text”.", "Le PDF ne contient pas de texte (probablement scanné). Photographiez les pages et utilisez « Image → texte ».")
_a("e_merge_min", "أرسل ملفين PDF على الأقل ثم اضغط «دمج».", "Send at least two PDFs, then press “Merge”.", "Envoyez au moins deux PDF puis appuyez sur « Fusionner ».")
_a("e_pages_syntax", "صيغة غير صحيحة. مثال: 1-3 أو 2,5,7-9", "Invalid format. Example: 1-3 or 2,5,7-9", "Format invalide. Exemple : 1-3 ou 2,5,7-9")
_a("e_pages_range", "الصفحة {p} خارج النطاق. عدد صفحات الملف: {n}", "Page {p} is out of range. The file has {n} pages.", "La page {p} n'existe pas. Le fichier a {n} pages.")
_a("e_stt_ffmpeg", "تعذر تجهيز أداة معالجة الصوت على الخادم.", "The audio converter is not available on the server.", "Le convertisseur audio n'est pas disponible sur le serveur.")
_a("e_stt_read", "تعذرت قراءة الملف الصوتي.", "Could not read the audio file.", "Impossible de lire le fichier audio.")
_a("e_stt_long", "التسجيل طويل جداً (الحد الأقصى نحو 10 دقائق).", "The recording is too long (about 10 minutes max).", "Enregistrement trop long (10 minutes max environ).")
_a("e_stt_net", "تعذر الاتصال بخدمة التعرف على الصوت، حاول لاحقاً.", "Could not reach the speech service. Try later.", "Service de reconnaissance vocale injoignable. Réessayez plus tard.")
_a("e_stt_empty", "لم أستطع استخراج كلام واضح من التسجيل.", "I couldn't extract clear speech from the recording.", "Impossible d'extraire une parole claire de l'enregistrement.")
_a("e_text_empty", "أرسل النص.", "Send some text.", "Envoyez du texte.")
_a("e_tts_long", "النص طويل (الحد 1000 حرف).", "Text too long (1000 characters max).", "Texte trop long (1000 caractères max).")
_a("e_text_long", "النص طويل (الحد {n} حرف).", "Text too long ({n} characters max).", "Texte trop long ({n} caractères max).")
_a("e_calc", "لم أفهم العملية. مثال: (5+3)*2^3 أو sqrt(144) أو sin(30)", "I didn't understand. Example: (5+3)*2^3 or sqrt(144) or sin(30)", "Expression non comprise. Exemple : (5+3)*2^3 ou sqrt(144) ou sin(30)")
_a("e_calc_zero", "لا يمكن القسمة على صفر.", "Cannot divide by zero.", "Division par zéro impossible.")
_a("e_calc_pow", "الأس كبير جداً.", "The exponent is too large.", "L'exposant est trop grand.")
_a("e_gpa", "اكتب كل مادة في سطر: النقاط ثم الساعات. مثال:\n4 3\n3.5 2\n3 4", "One course per line: points then hours. Example:\n4 3\n3.5 2\n3 4", "Une matière par ligne : points puis crédits. Exemple :\n4 3\n3.5 2\n3 4")
_a("e_units", "الصيغة: 10 km to m", "Format: 10 km to m", "Format : 10 km to m")
_a("e_units_unknown", "وحدة غير معروفة: {u}", "Unknown unit: {u}", "Unité inconnue : {u}")
_a("e_units_incompat", "لا يمكن التحويل بين وحدتين من نوعين مختلفين.", "Those two units are not compatible.", "Ces deux unités ne sont pas compatibles.")
_a("e_quad", "أرسل ثلاثة أرقام a b c. مثال: 1 -5 6", "Send three numbers a b c. Example: 1 -5 6", "Envoyez trois nombres a b c. Exemple : 1 -5 6")
_a("e_nums", "أرسل رقمين صحيحين موجبين أو أكثر. مثال: 12 18", "Send two or more positive integers. Example: 12 18", "Envoyez deux entiers positifs ou plus. Exemple : 12 18")
_a("e_sum_short", "النص قصير. أرسل 4 جمل على الأقل.", "Text too short. Send at least 4 sentences.", "Texte trop court. Envoyez au moins 4 phrases.")
_a("e_cite", "الصيغة: المؤلف | العنوان | السنة | الناشر أو الموقع", "Format: Author | Title | Year | Publisher or site", "Format : Auteur | Titre | Année | Éditeur ou site")
_a("e_date", "اكتب التاريخ بالصيغة YYYY-MM-DD مثل 2026-12-20", "Write the date as YYYY-MM-DD, e.g. 2026-12-20", "Écrivez la date AAAA-MM-JJ, ex. 2026-12-20")
_a("e_timer", "أرسل عدد الدقائق (من 1 إلى 180).", "Send the number of minutes (1 to 180).", "Envoyez le nombre de minutes (1 à 180).")
_a("e_translate", "تعذرت الترجمة الآن (قد يكون الحد اليومي للخدمة المجانية انتهى). حاول لاحقاً.", "Translation failed (the free service's daily limit may be used up). Try later.", "Échec de la traduction (la limite quotidienne du service gratuit est peut-être atteinte).")
_a("e_define_none", "لم أجد هذه الكلمة.", "I couldn't find that word.", "Mot introuvable.")
_a("e_define_net", "تعذر الاتصال بالقاموس. حاول لاحقاً.", "Could not reach the dictionary. Try later.", "Dictionnaire injoignable. Réessayez plus tard.")
_a("e_fmt", "الصيغ المدعومة: jpg, png, webp, pdf", "Supported formats: jpg, png, webp, pdf", "Formats pris en charge : jpg, png, webp, pdf")
_a("e_office_unsupported", "الصيغة غير مدعومة. المدعوم: docx, pptx, xlsx, txt", "Unsupported format. Supported: docx, pptx, xlsx, txt", "Format non pris en charge. Pris en charge : docx, pptx, xlsx, txt")
_a("e_office_empty", "لم أجد نصاً داخل الملف.", "I couldn't find any text in the file.", "Aucun texte trouvé dans le fichier.")
_a("e_font", "خط الطباعة غير متوفر على الخادم (ملف font.ttf).", "The print font is missing on the server (font.ttf).", "La police d'impression est absente du serveur (font.ttf).")
_a("e_too_many_pages", "الملف طويل جداً للتحويل هنا (الحد 30 صفحة).", "The document is too long to convert here (30 pages max).", "Document trop long pour la conversion (30 pages max).")

# ───────────── tool results ─────────────
_a("r_compress", "الحجم: {a} KB ← {b} KB", "Size: {a} KB → {b} KB", "Taille : {a} Ko → {b} Ko")
_a("r_gpa", "المعدل التراكمي: {gpa:.2f}\nمجموع الساعات: {hrs:g}", "GPA: {gpa:.2f}\nTotal hours: {hrs:g}", "Moyenne : {gpa:.2f}\nTotal des crédits : {hrs:g}")
_a("r_pdf2word_note", "ℹ️ تحويل نصي: النص فقط دون الصور والتنسيق.", "ℹ️ Text-only conversion: no images or layout.", "ℹ️ Conversion texte seul : sans images ni mise en page.")
_a("r_quad_two", "المعادلة لها جذران حقيقيان:\nx₁ = {x1}\nx₂ = {x2}\nالمميّز Δ = {d}", "Two real roots:\nx₁ = {x1}\nx₂ = {x2}\nDiscriminant Δ = {d}", "Deux racines réelles :\nx₁ = {x1}\nx₂ = {x2}\nDiscriminant Δ = {d}")
_a("r_quad_one", "جذر مكرر واحد:\nx = {x1}\nالمميّز Δ = 0", "One repeated root:\nx = {x1}\nDiscriminant Δ = 0", "Une racine double :\nx = {x1}\nDiscriminant Δ = 0")
_a("r_quad_none", "لا يوجد جذور حقيقية (Δ = {d}).\nالجذران المركّبان:\nx₁ = {x1}\nx₂ = {x2}", "No real roots (Δ = {d}).\nComplex roots:\nx₁ = {x1}\nx₂ = {x2}", "Pas de racines réelles (Δ = {d}).\nRacines complexes :\nx₁ = {x1}\nx₂ = {x2}")
_a("r_quad_linear", "المعادلة خطية: x = {x1}", "It is linear: x = {x1}", "Équation linéaire : x = {x1}")
_a("r_quad_degenerate", "لا يوجد حل محدد لهذه المدخلات.", "No unique solution for these inputs.", "Pas de solution unique pour ces valeurs.")
_a("r_nums", "القاسم المشترك الأكبر: {g}\nالمضاعف المشترك الأصغر: {l}\n\nالتحليل إلى عوامل أولية:\n{f}", "Greatest common divisor: {g}\nLeast common multiple: {l}\n\nPrime factors:\n{f}", "PGCD : {g}\nPPCM : {l}\n\nFacteurs premiers :\n{f}")
_a("r_wordcount", "الكلمات: {w}\nالأحرف (مع المسافات): {c}\nالأحرف (بدون مسافات): {c2}\nالجمل: {s}\nالفقرات: {p}\nزمن القراءة: نحو {m} دقيقة", "Words: {w}\nCharacters (with spaces): {c}\nCharacters (no spaces): {c2}\nSentences: {s}\nParagraphs: {p}\nReading time: about {m} min", "Mots : {w}\nCaractères (avec espaces) : {c}\nCaractères (sans espaces) : {c2}\nPhrases : {s}\nParagraphes : {p}\nTemps de lecture : environ {m} min")
_a("r_summary", "📝 ملخص تقريبي (أهم الجمل):\n\n{t}", "📝 Rough summary (key sentences):\n\n{t}", "📝 Résumé approximatif (phrases clés) :\n\n{t}")
_a("r_countdown", "⏳ المتبقي حتى {date}: {d} يوم (نحو {w} أسبوع).", "⏳ Time until {date}: {d} days (about {w} weeks).", "⏳ Il reste {d} jours jusqu'au {date} (environ {w} semaines).")
_a("r_countdown_today", "📅 الامتحان اليوم! بالتوفيق 🍀", "📅 The exam is today! Good luck 🍀", "📅 L'examen est aujourd'hui ! Bonne chance 🍀")
_a("r_countdown_past", "هذا التاريخ مضى بالفعل.", "That date has already passed.", "Cette date est déjà passée.")
_a("r_timer_set", "⏱ بدأ المؤقت: {m} دقيقة. سأنبهك عند الانتهاء.", "⏱ Timer started: {m} minutes. I'll ping you when it's over.", "⏱ Minuteur lancé : {m} minutes. Je vous préviendrai à la fin.")
_a("r_timer_done", "⏰ انتهى وقت المذاكرة ({m} دقيقة)! خذ استراحة قصيرة 🌿", "⏰ Study time is over ({m} min)! Take a short break 🌿", "⏰ Temps d'étude terminé ({m} min) ! Faites une courte pause 🌿")

# ───────────── payment (shown to students) ─────────────
_a("pay_off", "الدفع غير مفعّل حالياً.", "Payments are not enabled right now.", "Le paiement n'est pas activé pour le moment.")
_a("pay_info",
   "💳 اليوم المفتوح: استخدام غير محدود لمدة {hours} ساعة.\n\nالسعر: {price}\nرقم الحساب (بنكك): {account}\n{name_line}\n1) حوّل المبلغ إلى الحساب أعلاه.\n2) اضغط «أرسلت التحويل» ثم أرسل رقم العملية والمبلغ وصورة الإشعار.\n3) يتحقق البوت من الإشعار ويفعّل يومك خلال لحظات.",
   "💳 Day pass: unlimited use for {hours} hours.\n\nPrice: {price}\nAccount number (Bankak): {account}\n{name_line}\n1) Transfer the amount to the account above.\n2) Press “I sent the transfer”, then send the transaction number, amount and a screenshot of the receipt.\n3) The bot checks the receipt and activates your pass within moments.",
   "💳 Pass journée : usage illimité pendant {hours} h.\n\nPrix : {price}\nNuméro de compte (Bankak) : {account}\n{name_line}\n1) Transférez le montant vers le compte ci-dessus.\n2) Appuyez sur « J'ai envoyé le virement » puis envoyez le numéro d'opération, le montant et une capture du reçu.\n3) Le bot vérifie le reçu et active votre pass en quelques instants.")
_a("pay_name_line", "اسم الحساب: {name}\n", "Account name: {name}\n", "Nom du compte : {name}\n")
_a("pay_btn_sent", "✅ أرسلت التحويل", "✅ I sent the transfer", "✅ J'ai envoyé le virement")
_a("pay_ask_txn", "أرسل رقم العملية كما يظهر في إشعار بنكك:", "Send the transaction number exactly as shown in the receipt:", "Envoyez le numéro d'opération tel qu'indiqué sur le reçu :")
_a("pay_bad_txn", "⚠️ رقم العملية غير صحيح، أعد كتابته كما في الإشعار.", "⚠️ Invalid transaction number, retype it as in the receipt.", "⚠️ Numéro d'opération invalide, retapez-le comme sur le reçu.")
_a("pay_dup_txn", "⚠️ رقم العملية هذا مستخدم سابقاً.", "⚠️ This transaction number was already used.", "⚠️ Ce numéro d'opération a déjà été utilisé.")
_a("pay_ask_amount", "أرسل المبلغ الذي حوّلته (أرقام فقط):", "Send the amount you transferred (numbers only):", "Envoyez le montant viré (chiffres uniquement) :")
_a("pay_bad_amount", "⚠️ اكتب المبلغ بالأرقام فقط.", "⚠️ Write the amount in numbers only.", "⚠️ Écrivez le montant en chiffres uniquement.")
_a("pay_low_amount", "⚠️ المبلغ أقل من المطلوب ({price}).", "⚠️ The amount is lower than required ({price}).", "⚠️ Le montant est inférieur au prix ({price}).")
_a("pay_ask_photo", "أرسل الآن لقطة شاشة إشعار التحويل كاملة (كصورة وليس كملف):", "Now send a full screenshot of the receipt (as a photo, not a file):", "Envoyez maintenant la capture complète du reçu (en photo, pas en fichier) :")
_a("pay_order_hint", "أكمل الخطوات بالترتيب. المطلوب الآن: {what}", "Please follow the steps in order. Needed now: {what}", "Suivez les étapes dans l'ordre. Attendu : {what}")
_a("pay_w_txn", "رقم العملية.", "the transaction number.", "le numéro d'opération.")
_a("pay_w_amount", "المبلغ.", "the amount.", "le montant.")
_a("pay_w_photo", "صورة الإشعار (كصورة).", "the receipt photo (as a photo).", "la photo du reçu.")
_a("pay_pending", "لديك طلب قيد المراجعة بالفعل. انتظر قليلاً.", "You already have a request under review. Please wait.", "Vous avez déjà une demande en cours. Patientez.")
_a("pay_checking", "🔎 جارٍ فحص الإشعار...", "🔎 Checking the receipt...", "🔎 Vérification du reçu...")
_a("pay_ok", "✅ تم التحقق من التحويل! يومك المفتوح فعّال حتى {until}.", "✅ Transfer verified! Your day pass is active until {until}.", "✅ Virement vérifié ! Votre pass est actif jusqu'à {until}.")
_a("pay_retry", "⚠️ لم أستطع التأكد من الإشعار ({reason}). أرسل صورة أوضح للإشعار كاملاً (محاولة {n} من {mx}).", "⚠️ I couldn't confirm the receipt ({reason}). Send a clearer full screenshot (attempt {n} of {mx}).", "⚠️ Impossible de confirmer le reçu ({reason}). Envoyez une capture plus nette et complète (essai {n} sur {mx}).")
_a("pay_reject", "❌ تعذر التحقق من التحويل ({reason}). تأكد من البيانات وابدأ من جديد، أو تواصل مع المشرف.", "❌ Could not verify the transfer ({reason}). Check your details and start again, or contact the admin.", "❌ Virement non vérifié ({reason}). Vérifiez vos données et recommencez, ou contactez l'administrateur.")
_a("pay_manual_wait", "📨 تم استلام طلبك وسيراجعه المشرف قريباً وسيصلك إشعار هنا.", "📨 Request received. The admin will review it soon and you'll be notified here.", "📨 Demande reçue. L'administrateur la vérifiera bientôt et vous serez averti ici.")
_a("pay_approved_manual", "✅ تم تأكيد دفعتك! يومك المفتوح فعّال حتى {until}.", "✅ Payment confirmed! Your day pass is active until {until}.", "✅ Paiement confirmé ! Votre pass est actif jusqu'à {until}.")
_a("pay_rejected_manual", "❌ لم نتمكن من التأكد من التحويل. تأكد من رقم العملية والمبلغ وأعد المحاولة.", "❌ We couldn't confirm the transfer. Check the number and amount and try again.", "❌ Virement non confirmé. Vérifiez le numéro et le montant puis réessayez.")
_a("pay_revoked", "ℹ️ تم إلغاء تفعيل يومك المفتوح من قِبل المشرف.", "ℹ️ Your day pass was cancelled by the admin.", "ℹ️ Votre pass a été annulé par l'administrateur.")
_a("why_txn", "رقم العملية غير ظاهر في الصورة", "the transaction number is not visible in the image", "le numéro d'opération n'apparaît pas sur l'image")
_a("why_amount", "المبلغ غير ظاهر أو غير مطابق", "the amount is missing or doesn't match", "le montant est absent ou différent")
_a("why_old", "الإشعار قديم أو تاريخه غير صحيح", "the receipt is too old or its date is invalid", "le reçu est trop ancien ou sa date est invalide")
_a("why_recipient", "حساب المستلم غير مطابق", "the recipient doesn't match", "le destinataire ne correspond pas")
_a("why_ocr", "تعذرت قراءة الصورة", "the image could not be read", "l'image n'a pas pu être lue")
