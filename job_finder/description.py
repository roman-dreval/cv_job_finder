"""The job's description in the card (spec section 22): paragraphs, headings and lists as the site lays them out
(sources.html_to_text keeps them as "## " and "• "), the technologies the program finds coloured: green if the CV
has them, red if not."""
import html

from job_finder import grounding, style


def _coloured(line: str, known: set[str]) -> str:
    parts, done = [], 0
    for start, end, name in grounding.spans(line):
        color = style.MATCH_COLORS["yes" if name in known else "no"]
        parts.append(html.escape(line[done:start]))
        parts.append(f"<span style='color:{color}; font-weight:600'>{html.escape(line[start:end])}</span>")
        done = end
    parts.append(html.escape(line[done:]))
    return "".join(parts)


def to_html(text: str, known: set[str]) -> str:
    """Rich text for a QLabel; known: the CV's technologies."""
    parts, items = [], []

    def close_list():
        if items:
            parts.append("<ul style='margin-top:0; margin-bottom:10px; -qt-list-indent:1'>"
                         + "".join(f"<li style='margin-bottom:3px'>{item}</li>" for item in items) + "</ul>")
            items.clear()

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("• "):
            items.append(_coloured(line[2:].strip(), known))
            continue
        close_list()
        if line.startswith("## "):
            parts.append(f"<p style='margin-top:12px; margin-bottom:4px; font-weight:700'>"
                         f"{_coloured(line[3:].strip(), known)}</p>")
        elif line:
            parts.append(f"<p style='margin-top:0; margin-bottom:10px'>{_coloured(line, known)}</p>")
    close_list()
    return "".join(parts)
