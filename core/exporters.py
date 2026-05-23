from fpdf import FPDF
import textwrap


def generate_markdown(job, analysis):
    lines = []
    lines.append(f"# Tailored Resume")
    lines.append(f"")
    lines.append(f"_Tailored for: {job.job_title} at {job.company}_")
    lines.append(f"")
    lines.append("---")
    lines.append(f"")
    lines.append(analysis.tailored_resume)
    return "\n".join(lines)


def clean_pdf_text(text):
    if not text:
        return ""
    # Map common non-latin-1 Unicode characters to their latin-1 equivalents
    replacements = {
        "\u2014": "-",  # em dash
        "\u2013": "-",  # en dash
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u2022": "*",  # bullet
        "\u2026": "...", # ellipsis
        "\u00a0": " ",  # non-breaking space
        "\u20ac": "EUR", # euro sign
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    # Fallback to replace any other unencodable chars with '?' to prevent crashing
    return text.encode('latin-1', 'replace').decode('latin-1')


def generate_pdf(job, analysis):
    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, clean_pdf_text("Tailored Resume"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, clean_pdf_text(f"Tailored for: {job.job_title} at {job.company}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    pdf.ln(4)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

    content = analysis.tailored_resume
    lines = content.split("\n")

    for line in lines:
        stripped = line.strip()
        cleaned = clean_pdf_text(stripped)

        if cleaned.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 9, cleaned[2:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

        elif cleaned.startswith("## "):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 8, cleaned[3:].upper(), new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(180, 180, 180)
            pdf.set_line_width(0.2)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(3)

        elif cleaned.startswith("### "):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 7, cleaned[4:], new_x="LMARGIN", new_y="NEXT")

        elif cleaned.startswith("- ") or cleaned.startswith("* "):
            pdf.set_font("Helvetica", "", 10)
            bullet_text = "  -  " + cleaned[2:]
            pdf.multi_cell(0, 6, bullet_text, new_x="LMARGIN", new_y="NEXT")

        elif cleaned.startswith("_") and cleaned.endswith("_"):
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 6, cleaned.strip("_"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

        elif cleaned == "" or cleaned == "---":
            pdf.ln(2)

        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, cleaned, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
