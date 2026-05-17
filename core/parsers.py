import PyPDF2
from docx import Document


def extract_text_from_pdf(file):
    try:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Could not read PDF file: {str(e)}")


def extract_text_from_docx(file):
    try:
        doc = Document(file)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(paragraphs).strip()
    except Exception as e:
        raise ValueError(f"Could not read DOCX file: {str(e)}")


def extract_resume_text(uploaded_file):
    filename = uploaded_file.name.lower()
    if filename.endswith('.pdf'):
        return extract_text_from_pdf(uploaded_file)
    elif filename.endswith('.docx'):
        return extract_text_from_docx(uploaded_file)
    else:
        raise ValueError(
            "Unsupported file type. Please upload a PDF or DOCX file."
        )