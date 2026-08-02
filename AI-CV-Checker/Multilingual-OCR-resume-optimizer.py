# ==============================================================================
# 🚀 AI CV CHECKER: RESUME OPTIMIZATION AGENT (KAGGLE GRADIO + MULTILINGUAL + OCR)
# ==============================================================================
# This specialized script is designed to run 100% self-contained in a single cell or page on Kaggle or Google Colab.
# This version is equipped with the following features:
# 1. Sleek and smart web user interface powered by Gradio.
# 2. Error-free PDF OCR system (Persian and English) using the powerful Gemini 3.6 Flash vision model.
# 3. Final resume language selection capability (Persian or English).
# 4. Download final optimized files in both Word (.docx) and Markdown (.md) formats.
#
# Prerequisites:
# 1. Enable Internet in Kaggle's right-side panel settings (Internet On).
# 2. Obtain a free API key from: https://aistudio.google.com/
# 3. Place the key in Kaggle's Add-ons -> Secrets named GEMINI_API_KEY (recommended) or enter it in the input field in the Gradio UI.
# ==============================================================================

import os
import sys
import json
import tempfile

# ------------------------------------------------------------------------------
# 1. Automatic installation of dependencies on the Kaggle server
# ------------------------------------------------------------------------------
print("[*] Installing required libraries (google-genai, python-docx, gradio, nest-asyncio)...")
try:
    import google.genai as genai
    import docx
    import gradio as gr
    import nest_asyncio
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "google-genai", "python-docx", "gradio", "nest-asyncio"])
    print("[+] Dependencies installed successfully!")

# Final import of packages after successful installation
from google import genai
from google.genai import types
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import gradio as gr
import nest_asyncio

# Enable support for nested event loops in Jupyter notebooks
nest_asyncio.apply()

# ------------------------------------------------------------------------------
# 2. Text extraction helper for Word documents (.docx)
# ------------------------------------------------------------------------------
def extract_text_from_docx(file_path):
    if not file_path:
        return ""
    try:
        doc = docx.Document(file_path)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
        # Extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    text.append(" | ".join(row_text))
        return "\n".join(text)
    except Exception as e:
        return f"خطا در خواندن فایل ورد: {str(e)}"

# ------------------------------------------------------------------------------
# 3. Design and generate a highly polished Word document with standard executive styling
# ------------------------------------------------------------------------------
def save_optimized_docx(markdown_text, output_path="optimized_resume.docx"):
    try:
        doc = docx.Document()
        
        # Check for Persian characters in the text to determine Right-To-Left (RTL) alignment
        is_rtl = any('\u0600' <= char <= '\u06FF' for char in markdown_text)
        
        # Page Setup: Standard margins (0.75 inch)
        for section in doc.sections:
            section.top_margin = Inches(0.75)
            section.bottom_margin = Inches(0.75)
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)
            
        # Global Styles
        style_normal = doc.styles['Normal']
        font = style_normal.font
        font.name = 'Arial' # Use highly compatible font for Persian and English
        font.size = Pt(11)
        font.color.rgb = RGBColor(40, 40, 40)
        style_normal.paragraph_format.line_spacing = 1.2
        style_normal.paragraph_format.space_after = Pt(4)
        
        def add_run(p, text, bold=False, italic=False, size_pt=None, color_rgb=None):
            run = p.add_run(text)
            run.bold = bold
            run.italic = italic
            if size_pt:
                run.font.size = Pt(size_pt)
            if color_rgb:
                run.font.color.rgb = color_rgb
            if is_rtl:
                rPr = run._r.get_or_add_rPr()
                rtl = OxmlElement('w:rtl')
                rPr.append(rtl)
                
                # Set beautiful Tahoma font for RTL (Right-to-Left) languages
                rFonts = OxmlElement('w:rFonts')
                rFonts.set(qn('w:ascii'), 'Tahoma')
                rFonts.set(qn('w:hAnsi'), 'Tahoma')
                rFonts.set(qn('w:cs'), 'Tahoma')
                rPr.append(rFonts)
                
                # Set font size for RTL text
                if size_pt:
                    szCs = OxmlElement('w:szCs')
                    szCs.set(qn('w:val'), str(int(size_pt * 2)))
                    rPr.append(szCs)
                    
                # Set bold formatting for RTL text
                if bold:
                    bCs = OxmlElement('w:bCs')
                    rPr.append(bCs)
            return run

        def create_paragraph(style=None):
            if style:
                p = doc.add_paragraph(style=style)
            else:
                p = doc.add_paragraph()
            if is_rtl:
                pPr = p._p.get_or_add_pPr()
                bidi = OxmlElement('w:bidi')
                pPr.append(bidi)
            return p
        
        lines = markdown_text.split('\n')
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
                
            # Header 1: Name and applicant's title (large, bold, and centered)
            if line_str.startswith('# '):
                p = create_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(12)
                p.paragraph_format.space_after = Pt(6)
                add_run(p, line_str[2:], bold=True, size_pt=18, color_rgb=RGBColor(26, 54, 93))
                
            # Header 2: Main sections of the resume (medium size and blue color)
            elif line_str.startswith('## '):
                p = create_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if not is_rtl else WD_ALIGN_PARAGRAPH.RIGHT
                p.paragraph_format.space_before = Pt(14)
                p.paragraph_format.space_after = Pt(4)
                add_run(p, line_str[3:], bold=True, size_pt=13, color_rgb=RGBColor(44, 82, 130))
                
            # Header 3: Job title or companies (bold, dark, and normal size)
            elif line_str.startswith('### '):
                p = create_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if not is_rtl else WD_ALIGN_PARAGRAPH.RIGHT
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(2)
                add_run(p, line_str[4:], bold=True, size_pt=11, color_rgb=RGBColor(74, 85, 104))
                
            # Bullet points
            elif line_str.startswith('* ') or line_str.startswith('- '):
                if is_rtl:
                    # Use normal right-aligned paragraph instead of English List Bullet style
                    p = create_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    p.paragraph_format.space_after = Pt(3)
                    p.paragraph_format.right_indent = Pt(12) # Indent from right for list items
                    bullet_text = "• "
                else:
                    p = create_paragraph(style='List Bullet')
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    p.paragraph_format.space_after = Pt(3)
                    bullet_text = ""
                
                parts = (bullet_text + line_str[2:]).split('**')
                is_bold = False
                for part in parts:
                    add_run(p, part, bold=is_bold)
                    is_bold = not is_bold
                    
            # Normal text
            else:
                p = create_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if not is_rtl else WD_ALIGN_PARAGRAPH.RIGHT
                p.paragraph_format.space_after = Pt(6)
                
                parts = line_str.split('**')
                is_bold = False
                for part in parts:
                    add_run(p, part, bold=is_bold)
                    is_bold = not is_bold
                    
        doc.save(output_path)
        return True
    except Exception as e:
        print(f"[-] Error writing Word document: {e}")
        return False

# ------------------------------------------------------------------------------
# 4. Core Resume Intelligent Processing (Gemini Optimization Engine)
# ------------------------------------------------------------------------------
def run_cv_checker_process(api_key, resume_file, resume_text, jd_text, mode, target_lang):
    # Set access key
    active_key = None
    if api_key and api_key.strip():
        active_key = api_key.strip().strip("'\"`[]{}")
    else:
        # Try to read Kaggle Secret if manual key is not provided
        try:
            from kaggle_secrets import UserSecretsClient
            user_secrets = UserSecretsClient()
            active_key = user_secrets.get_secret("GEMINI_API_KEY")
            if active_key:
                active_key = active_key.strip().strip("'\"`[]{}")
        except Exception:
            pass
            
    if not active_key or active_key in ["YOUR_API_KEY", "YOUR_GEMINI_API_KEY", ""]:
        return (
            "⚠️ خطا: کلید دسترسی Gemini API یافت نشد! لطفاً یک کلید معتبر از Google AI Studio دریافت کرده و آن را در فیلد مربوطه وارد کنید یا به سکرت کگل اضافه کنید.",
            "", "", "", "", "", None, None, "❌ کلید API یافت نشد"
        )

    os.environ["GEMINI_API_KEY"] = active_key

    # Extract resume content
    final_resume_content = ""
    extracted_via_ocr = False
    ocr_log_message = "متن ورودی عادی"
    
    try:
        client = genai.Client(api_key=active_key)
    except Exception as e:
        return (
            f"⚠️ خطا در راه‌اندازی کلاینت Gemini: {str(e)}",
            "", "", "", "", "", None, None, "❌ خطا در راه‌اندازی"
        )

    if resume_file is not None:
        file_ext = os.path.splitext(resume_file.name)[1].lower()
        if file_ext == ".docx":
            final_resume_content = extract_text_from_docx(resume_file.name)
            ocr_log_message = "✅ استخراج متن از سند Word (.docx)"
        elif file_ext == ".pdf":
            print("[*] PDF detected. Copying to safe ASCII filename to avoid encoding issues and uploading to Gemini File API...")
            temp_pdf_path = None
            try:
                import shutil
                # Create a safe ASCII file copy path to prevent Unicode header issues
                temp_pdf_path = os.path.join(os.path.dirname(resume_file.name), "temp_resume_for_ocr.pdf")
                shutil.copy2(resume_file.name, temp_pdf_path)

                # Upload the temporary file to Gemini for high-accuracy vision analysis
                uploaded_file = client.files.upload(file=temp_pdf_path)
                
                # Request error-free text extraction
                ocr_prompt = (
                    "Please analyze this PDF document and perform 100% accurate, zero-error text extraction (OCR). "
                    "Extract all text exactly as written in its original language, preserving all numbers, dates, emails, and phone numbers. "
                    "CRITICAL REQUIREMENT: For Persian (Farsi) text, you MUST extract and write it in the Persian language using Farsi script. "
                    "DO NOT translate Persian words to English, and DO NOT transliterate Persian words into English characters. "
                    "For Persian RTL (راست به چپ) text, do not reverse characters or mess up the word ordering. "
                    "Return ONLY the clean extracted text of the resume, preserving its structural sections and original language (either English or Persian). "
                    "Do not translate it, do not summarize it, and do not paraphrase it."
                )
                
                ocr_response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[uploaded_file, ocr_prompt]
                )
                
                final_resume_content = ocr_response.text.strip()
                extracted_via_ocr = True
                ocr_log_message = "✅ استخراج بی‌نظیر متن PDF با سیستم بینایی هوش مصنوعی Gemini (بدون خطای کاراکتر)"
                
                # Clean up file from Google servers
                try:
                    client.files.delete(name=uploaded_file.name)
                except Exception:
                    pass
            except Exception as e:
                err_msg = str(e)
                if "API key not valid" in err_msg or "API_KEY_INVALID" in err_msg or "INVALID_ARGUMENT" in err_msg:
                    return (
                        "⚠️ کلید دسترسی Gemini API شما نامعتبر است. لطفاً مطمئن شوید که یک کلید API معتبر از Google AI Studio (https://aistudio.google.com) دریافت کرده و آن را بدون کاراکترهای اضافی وارد کرده‌اید.",
                        "", "", "", "", "", None, None, "❌ کلید API نامعتبر"
                    )
                return (
                    f"⚠️ خطا در پردازش OCR فایل PDF: {err_msg}",
                    "", "", "", "", "", None, None, "❌ خطای پردازش PDF"
                )
            finally:
                # Clean up local temporary file
                if temp_pdf_path and os.path.exists(temp_pdf_path):
                    try:
                        os.remove(temp_pdf_path)
                    except Exception:
                        pass
        else:
            try:
                with open(resume_file.name, "r", encoding="utf-8") as f:
                    final_resume_content = f.read()
                ocr_log_message = "✅ استخراج متن از فایل متنی ساده (.txt)"
            except Exception as e:
                return (
                    f"⚠️ خطا در خواندن فایل متنی: {str(e)}",
                    "", "", "", "", "", None, None, "❌ خطای خواندن فایل"
                )
                
    if not final_resume_content and resume_text:
        final_resume_content = resume_text
        ocr_log_message = "✅ استفاده از متن پیست شده مستقیم کاربر"

    if not final_resume_content.strip():
        return (
            "⚠️ خطا: محتوای رزومه یافت نشد! لطفا یا فایل رزومه را آپلود کنید یا متن آن را پیست کنید.",
            "", "", "", "", "", None, None, "❌ محتوای خالی"
        )

    if not jd_text or not jd_text.strip():
        return (
            "⚠️ خطا: لطفا شرح شغل هدف (Job Description) را وارد کنید.",
            "", "", "", "", "", None, None, "❌ شرح شغل خالی"
        )

    # Communicate with Gemini 3.6 Flash to apply optimization
    try:
        system_instruction = (
            "You are an elite, highly experienced technical recruiter and professional resume writer (ATS expert).\n"
            "Your goal is to optimize, rewrite, and 'morph' the user's base resume to align perfectly with the target Job Description (JD).\n"
            "Provide your entire response as a strict JSON structure matching the schema specified so that the calling system can parse it reliably."
        )
        
        prompt = f"""
=== USER BASE RESUME ===
{final_resume_content}

=== TARGET JOB DESCRIPTION (JD) ===
{jd_text}

=== OPTIMIZATION MODE ===
{mode} (comprehensive = full rewrite, keywords = focus on ATS matches, impact = focus on quantifiable metrics, concise = fit in one page)

=== TARGET OUTPUT LANGUAGE ===
{target_lang} (en = The final optimized resume and all feedback MUST be written in English, fa = The final optimized resume and all feedback MUST be written in Persian/فارسی)

=== INSTRUCTIONS ===
Perform CV Checker optimization:
1. Conduct a deep gap analysis identifying missing skills, mismatch of titles, and weak bullet points.
2. Inject critical keywords, metrics, and action verbs into the resume.
3. Completely rewrite the resume in high-quality professional Markdown format.
4. Adapt the output strictly to the TARGET OUTPUT LANGUAGE. If TARGET OUTPUT LANGUAGE is 'fa', the "optimized_markdown" and all analysis/feedback fields MUST be written in fluent, grammatically correct Persian (Farsi script). All professional job descriptions, responsibilities, actions, and achievements originally written in Persian MUST remain in Persian. DO NOT translate Persian terms to English. Keep only standard technical keywords/names of tools (like 'Python', 'FastAPI', 'Docker', etc.) in English, while all surrounding text, summaries, and bullet points MUST be written in high-quality Persian. If TARGET OUTPUT LANGUAGE is 'en', they must be in English.
5. Provide the result in a valid JSON format. The JSON must contain exactly two top-level keys:
   - "optimized_markdown": The full, ready-to-use polished resume in Markdown.
   - "analysis": A JSON object containing:
     - "score_before": An ATS match score before (integer 0-100)
     - "score_after": An ATS match score after (integer 0-100)
     - "gaps_solved": List of strings describing critical gaps solved
     - "tailored_keywords": List of keywords integrated
     - "action_verbs_injected": List of action verbs used to elevate experience bullets
     - "metrics_added": List of metrics/results simulated/added based on raw points
     - "general_feedback": Strategic feedback for the candidate
     - "gap_analysis": {{
         "missing_keywords": List of keywords still missing or recommended to learn
         "matched_keywords": List of keywords successfully matched
         "strength_score": Match score strength (integer 0-100)
         "suggestions": List of concrete recommendations
       }}

Return ONLY valid JSON. Start your response with {{ and end with }}. Do not wrap it in markdown code blocks or add any trailing text.
"""

        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.15,
                response_mime_type="application/json"
            )
        )
        
        raw_json = response.text.strip()
        if raw_json.startswith("```json"):
            raw_json = raw_json[7:]
        if raw_json.endswith("```"):
            raw_json = raw_json[:-3]
        raw_json = raw_json.strip()
        
        result = json.loads(raw_json)
        optimized_markdown = result.get("optimized_markdown", "")
        analysis = result.get("analysis", {})
        
        # Calculate statistics and analysis to present a beautiful output
        score_before = analysis.get("score_before", 0)
        score_after = analysis.get("score_after", 0)
        
        # Design matching score widget in HTML format
        score_html = f"""
        <div style="display: flex; justify-content: space-around; align-items: center; background: #0f172a; padding: 20px; border-radius: 12px; border: 1px solid #1e293b; color: white; text-align: center; font-family: 'Tahoma', sans-serif;">
            <div>
                <p style="margin: 0; color: #94a3b8; font-size: 14px;">امتیاز تطابق اولیه</p>
                <h1 style="margin: 5px 0 0 0; color: #ef4444; font-size: 42px; font-weight: bold;">{score_before}%</h1>
            </div>
            <div style="font-size: 28px; color: #64748b;">➡️</div>
            <div>
                <p style="margin: 0; color: #94a3b8; font-size: 14px;">امتیاز پس از بهینه‌سازی (CV Checker)</p>
                <h1 style="margin: 5px 0 0 0; color: #22c55e; font-size: 42px; font-weight: bold;">{score_after}%</h1>
            </div>
            <div style="border-right: 1px solid #334155; height: 50px; margin: 0 10px;"></div>
            <div>
                <p style="margin: 0; color: #94a3b8; font-size: 14px;">میزان بهبود پتانسیل مصاحبه</p>
                <h1 style="margin: 5px 0 0 0; color: #3b82f6; font-size: 38px; font-weight: bold;">+{score_after - score_before}%</h1>
            </div>
        </div>
        """
        
        # Format the gap analysis information
        gaps_text = "\n".join([f"✅ {gap}" for gap in analysis.get("gaps_solved", [])])
        keywords_text = ", ".join(analysis.get("tailored_keywords", []))
        feedback_text = analysis.get("general_feedback", "")
        
        gap_details = analysis.get("gap_analysis", {})
        suggestions_list = gap_details.get("suggestions", [])
        suggestions_text = "\n".join([f"📌 {sug}" for sug in suggestions_list])
        
        # Generate and save physical files for the user to download
        temp_dir = tempfile.gettempdir()
        docx_path = os.path.join(temp_dir, "optimized_resume.docx")
        md_path = os.path.join(temp_dir, "optimized_resume.md")
        
        save_optimized_docx(optimized_markdown, docx_path)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(optimized_markdown)
            
        return (
            score_html,
            optimized_markdown,
            feedback_text,
            gaps_text,
            keywords_text,
            suggestions_text,
            docx_path,
            md_path,
            ocr_log_message
        )
        
    except Exception as e:
        err_msg = str(e)
        if "API key not valid" in err_msg or "API_KEY_INVALID" in err_msg or "INVALID_ARGUMENT" in err_msg:
            return (
                "⚠️ کلید دسترسی Gemini API شما نامعتبر است. لطفاً مطمئن شوید که یک کلید API معتبر از Google AI Studio (https://aistudio.google.com) دریافت کرده و آن را بدون کاراکترهای اضافی وارد کرده‌اید.",
                "", "", "", "", "", None, None, "❌ کلید API نامعتبر"
            )
        return (
            f"⚠️ بروز خطا در فرآیند پردازش هوشمند: {err_msg}",
            "", "", "", "", "", None, None, f"❌ خطای وب سرویس: {err_msg}"
        )

# ------------------------------------------------------------------------------
# 5. Gradio Web User Interface (Gradio Web UI)
# ------------------------------------------------------------------------------
# Build custom modern UI with Gradio
with gr.Blocks(title="AI CV Checker - دستیار هوشمند بهینه‌سازی رزومه کگل", theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate")) as demo:
    gr.HTML("""
    <div style="text-align: center; margin-bottom: 25px; padding: 15px; border-radius: 12px; background: linear-gradient(135deg, #1e3a8a, #0d9488); color: white;">
        <h1 style="margin: 0; font-size: 28px; font-weight: bold;">🚀 دستیار هوشمند بهینه‌سازی رزومه (AI CV Checker)</h1>
        <p style="margin: 8px 0 0 0; font-size: 15px;">سیستم انطباق عمیق و بازنویسی رزومه متناسب با شرح شغل هدف مبتنی بر هوش مصنوعی Gemini 3.6 Flash</p>
    </div>
    """)
    
    with gr.Row():
        # Left Panel: Inputs
        with gr.Column(scale=1):
            gr.Markdown("### 📥 اطلاعات ورودی و تنظیمات")
            
            api_key_input = gr.Textbox(
                label="🔑 کلید دسترسی Gemini API (در صورت خالی بودن از سکرت کگل یا متغیر محیطی استفاده می‌شود)",
                placeholder="AIzaSy...",
                type="password"
            )
            
            with gr.Tabs():
                with gr.TabItem("📄 آپلود فایل رزومه"):
                    resume_file_input = gr.File(
                        label="فایل رزومه فعلی خود را آپلود کنید (پشتیبانی کامل از PDF فارسی/انگلیسی، Word و TXT)",
                        file_types=[".docx", ".txt", ".pdf"]
                    )
                with gr.TabItem("✍️ کپی-پیست متن رزومه"):
                    resume_text_input = gr.Textbox(
                        label="متن رزومه خود را در این بخش پیست کنید",
                        placeholder="نام، سوابق کاری، تحصیلات و مهارت‌ها...",
                        lines=10
                    )
                    
            jd_input = gr.Textbox(
                label="🎯 شرح شغل هدف (Job Description)",
                placeholder="نیازمندی‌ها، مهارت‌های مورد نیاز و مسئولیت‌های پوزیشن شغلی مورد نظر را اینجا قرار دهید...",
                lines=8
            )
            
            with gr.Row():
                target_lang_input = gr.Radio(
                    choices=[
                        ("fa", "فارسی (Persian)"),
                        ("en", "انگلیسی (English)")
                    ],
                    value="fa",
                    label="🌐 زبان رزومه بهینه‌سازی شده نهایی"
                )
                
                mode_input = gr.Radio(
                    choices=[
                        ("comprehensive", "همه‌جانبه (بنویس دوباره)"),
                        ("keywords", "تزریق کلمات کلیدی ATS"),
                        ("impact", "تزریق سنجه‌های عددی"),
                        ("concise", "خلاصه در یک صفحه")
                    ],
                    value="comprehensive",
                    label="⚙️ حالت بهینه‌سازی ایجنت"
                )
            
            submit_btn = gr.Button("🚀 تحلیل و بازنویسی هوشمند رزومه", variant="primary")
            
        # Right Panel: Outputs
        with gr.Column(scale=1.2):
            gr.Markdown("### 📊 نتایج بهینه‌سازی و تحلیل خلاءها")
            
            # System status and log widget
            with gr.Row():
                status_log = gr.Textbox(
                    label="ℹ️ وضعیت پردازش فایل ورودی (OCR Status)",
                    value="آماده به کار",
                    interactive=False
                )
            
            # Score comparison widget
            score_output = gr.HTML(value="""
            <div style="background: #1e293b; padding: 25px; border-radius: 12px; border: 1px dashed #475569; text-align: center; color: #94a3b8;">
                منتظر شروع تحلیل... کلید "تحلیل و بازنویسی هوشمند رزومه" را فشار دهید تا فرآیند آغاز شود.
            </div>
            """)
            
            with gr.Tabs():
                with gr.TabItem("✨ رزومه بهینه‌سازی شده"):
                    preview_output = gr.Markdown(label="پیش‌نمایش رزومه جدید شما")
                
                with gr.TabItem("💡 توصیه‌های مربی حرفه‌ای"):
                    feedback_output = gr.Textbox(label="توصیه‌ها و استراتژی مصاحبه", lines=12, interactive=False)
                    
                with gr.TabItem("🔍 خلاءهای حل شده"):
                    gaps_output = gr.Textbox(label="خلاءهای شناسایی شده و راهکارهای اعمال شده", lines=6, interactive=False)
                    keywords_output = gr.Textbox(label="واژگان کلیدی تزریق شده به رزومه", lines=3, interactive=False)
                    suggestions_output = gr.Textbox(label="توصیه‌های تکمیلی برای یادگیری و بهبود رزومه", lines=6, interactive=False)
            
            gr.Markdown("### 💾 دانلود فایل‌های نهایی")
            with gr.Row():
                docx_download = gr.File(label="📥 دانلود فایل Word (.docx)")
                md_download = gr.File(label="📥 دانلود فایل Markdown (.md)")

    # Define submit button click event
    submit_btn.click(
        fn=run_cv_checker_process,
        inputs=[
            api_key_input,
            resume_file_input,
            resume_text_input,
            jd_input,
            mode_input,
            target_lang_input
        ],
        outputs=[
            score_output,
            preview_output,
            feedback_output,
            gaps_output,
            keywords_output,
            suggestions_output,
            docx_download,
            md_download,
            status_log
        ]
    )

# ------------------------------------------------------------------------------
# 6. Run the Web Application
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Enable share=True for Kaggle and Colab to allow easy web access
    print("[*] Starting Gradio UI with Multilingual Target and Visual PDF OCR support...")
    demo.launch(share=True, show_error=True)
