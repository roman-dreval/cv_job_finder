from job_finder import description, style

GREEN, RED = style.MATCH_COLORS["yes"], style.MATCH_COLORS["no"]


def test_headings_lists_and_paragraphs():
    text = "## Requirements:\n• Git\n• Linux\n\nWe offer a team <3 & coffee."
    result = description.to_html(text, set())
    assert result.index("Requirements:") < result.index("<ul") < result.index("Git") < result.index("</ul>")
    assert "font-weight:700'>Requirements:</p>" in result
    assert result.count("<li") == 2 and "• " not in result and "## " not in result
    assert "We offer a team &lt;3 &amp; coffee.</p>" in result


def test_technologies_are_coloured_by_the_cv():
    result = description.to_html("Zkušenosti s Pythonem, Docker výhodou.", {"Python"})
    assert f"<span style='color:{GREEN}; font-weight:600'>Pythonem</span>" in result
    assert f"<span style='color:{RED}; font-weight:600'>Docker</span>" in result


def test_an_old_plain_text_and_nothing():
    assert description.to_html("Line one\nLine two", set()).count("<p") == 2
    assert description.to_html("", set()) == ""
