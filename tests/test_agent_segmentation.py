from src.agent.segmentation import normalize_text, segment

GREENHOUSE_HTML = (
    "<p>Figma is building a better way to design.</p>"
    "<h3><strong>What you'll do at Figma:</strong></h3>"
    "<ul><li>Build and ship LLM-powered features</li><li>Own the retrieval pipeline</li></ul>"
    "<h3>We'd love to hear from you if you have:</h3>"
    "<ul><li>3+ years of Python</li><li>Experience with vector search</li></ul>"
    "<h3>How we'll take care of you</h3><p>Health, dental and vision.</p>"
)


def kinds(text):
    return [s.kind for s in segment(text)]


def test_normalize_strips_html_and_keeps_structure():
    text = normalize_text(GREENHOUSE_HTML)
    assert "<" not in text and ">" not in text
    assert "- Build and ship LLM-powered features" in text
    assert "What you'll do at Figma:" in text.split("\n")


def test_normalize_plain_text_is_untouched_apart_from_whitespace():
    assert normalize_text("Hello   world\r\n\r\n\r\n\r\nbye") == "Hello world\n\nbye"


def test_normalize_does_not_treat_angle_brackets_in_prose_as_html():
    text = "We want x < y and templates like Vec<int> in C++"
    assert normalize_text(text) == text


def test_normalize_empty():
    assert normalize_text("") == ""
    assert segment("   ") == []


def test_greenhouse_sections_are_classified():
    text = normalize_text(GREENHOUSE_HTML)
    assert kinds(text) == ["intro", "responsibilities", "requirements", "benefits"]


def test_offsets_index_the_normalized_text():
    text = normalize_text(GREENHOUSE_HTML)
    for s in segment(text):
        assert text[s.start:s.end] == s.text
        assert s.text == s.text.strip()


def test_responsibilities_segment_holds_the_duties_not_the_requirements():
    text = normalize_text(GREENHOUSE_HTML)
    resp = next(s for s in segment(text) if s.kind == "responsibilities")
    assert "retrieval pipeline" in resp.text
    assert "3+ years" not in resp.text


def test_unstructured_post_is_one_unclassified_segment():
    post = "Acme | NYC | ONSITE | Backend engineer. We build payment rails in Go. Email jobs@acme.com"
    segs = segment(post)
    assert [s.kind for s in segs] == ["unclassified"]
    assert segs[0].text == post


def test_long_sentences_are_not_mistaken_for_headings():
    text = "Responsibilities include building and shipping many things for a very large number of customers every day of the week."
    assert kinds(text) == ["unclassified"]


def test_bulleted_lines_are_not_headings():
    text = "Intro line\n- Requirements are strict\nmore text"
    assert kinds(text) == ["unclassified"]


def test_french_headings():
    text = "Bienvenue\nUne journée typique\nVous construisez des outils.\nVotre expertise\n5 ans de Python."
    assert kinds(text) == ["intro", "responsibilities", "requirements"]


def test_text_starting_with_heading_has_no_intro():
    text = "Responsibilities\nBuild things\nRequirements\nPython"
    assert kinds(text) == ["responsibilities", "requirements"]
