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


def generate_pdf(job, analysis):
    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Tailored Resume", ln=True)

    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, f"Tailored for: {job.job_title} at {job.company}", ln=True)
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

        if stripped.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 9, stripped[2:])
            pdf.ln(1)

        elif stripped.startswith("## "):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 8, stripped[3:].upper())
            pdf.set_draw_color(180, 180, 180)
            pdf.set_line_width(0.2)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(3)

        elif stripped.startswith("### "):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 7, stripped[4:])

        elif stripped.startswith("- ") or stripped.startswith("* "):
            pdf.set_font("Helvetica", "", 10)
            bullet_text = "  •  " + stripped[2:]
            pdf.multi_cell(0, 6, bullet_text)

        elif stripped.startswith("_") and stripped.endswith("_"):
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 6, stripped.strip("_"))
            pdf.set_text_color(0, 0, 0)

        elif stripped == "" or stripped == "---":
            pdf.ln(2)

        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, stripped)

    return bytes(pdf.output())