import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def render_markdown(text):
    if not text:
        return ''
    md = markdown.Markdown(extensions=[
        'extra',        # tables, fenced code, footnotes
        'nl2br',        # newlines become <br> — important for resume content
        'sane_lists',   # cleaner list handling
    ])
    return mark_safe(md.convert(text))