#!/usr/bin/env python3
"""Tests for og_tags.py — run with: python3 test_og_tags.py"""

import unittest

from og_tags import inject_og_tags, validate_og_tags, extract_title_and_description


SAMPLE_WITH_TITLE_H1 = """<!doctype html>
<html>
<head><title>Page Title</title></head>
<body><h1>Heading Title</h1><p>This is the first paragraph of body text. It has more after.</p></body>
</html>"""

SAMPLE_NO_HEAD = """<!doctype html>
<html>
<body><h1>Only A Heading</h1><p>Some body copy for the summary.</p></body>
</html>"""

SAMPLE_BARE_FRAGMENT = "<div><h1>Fragment Heading</h1><p>Fragment body text here.</p></div>"

SAMPLE_WITH_META_DESC = """<html><head>
<title>Has Meta</title>
<meta name="description" content="Existing meta description.">
</head><body><h1>H1</h1></body></html>"""


class TestExtraction(unittest.TestCase):
    def test_prefers_title_tag_over_h1(self):
        title, _ = extract_title_and_description(SAMPLE_WITH_TITLE_H1)
        self.assertEqual(title, "Page Title")

    def test_falls_back_to_h1_when_no_title(self):
        title, _ = extract_title_and_description(SAMPLE_NO_HEAD)
        self.assertEqual(title, "Only A Heading")

    def test_overrides_win(self):
        title, desc = extract_title_and_description(
            SAMPLE_WITH_TITLE_H1, title_override="Custom", description_override="Custom desc."
        )
        self.assertEqual(title, "Custom")
        self.assertEqual(desc, "Custom desc.")

    def test_prefers_existing_meta_description(self):
        _, desc = extract_title_and_description(SAMPLE_WITH_META_DESC)
        self.assertEqual(desc, "Existing meta description.")

    def test_generates_one_sentence_summary_from_body(self):
        _, desc = extract_title_and_description(SAMPLE_WITH_TITLE_H1)
        self.assertEqual(desc, "This is the first paragraph of body text.")


class TestInjection(unittest.TestCase):
    def test_inserts_into_existing_head(self):
        result = inject_og_tags(SAMPLE_WITH_TITLE_H1, url="https://claude.ai/artifact/abc")
        self.assertIn('<meta property="og:title" content="Page Title">', result)
        self.assertIn('property="og:type" content="website"', result)
        self.assertIn('property="og:url" content="https://claude.ai/artifact/abc"', result)
        head_pos = result.index("<head>") if "<head>" in result else result.index("<head")
        og_pos = result.index('property="og:title"')
        self.assertLess(head_pos, og_pos)

    def test_creates_head_when_missing(self):
        result = inject_og_tags(SAMPLE_NO_HEAD)
        self.assertIn("<head>", result)
        self.assertIn('property="og:title"', result)

    def test_handles_bare_fragment_without_html_tag(self):
        result = inject_og_tags(SAMPLE_BARE_FRAGMENT)
        self.assertIn('property="og:title"', result)
        self.assertIn("Fragment Heading", result)

    def test_escapes_special_characters(self):
        html_in = '<html><head><title>A & B "Quoted" <Tag></title></head><body></body></html>'
        result = inject_og_tags(html_in)
        self.assertIn("&amp;", result)
        self.assertNotIn('content="A & B', result)

    def test_idempotent_on_rerun(self):
        once = inject_og_tags(SAMPLE_WITH_TITLE_H1, url="https://claude.ai/artifact/abc")
        twice = inject_og_tags(once, url="https://claude.ai/artifact/abc")
        self.assertEqual(once.count('property="og:title"'), 1)
        self.assertEqual(twice.count('property="og:title"'), 1)

    def test_rerun_with_new_values_replaces_old(self):
        once = inject_og_tags(SAMPLE_WITH_TITLE_H1, title="Old Title")
        twice = inject_og_tags(once, title="New Title")
        self.assertNotIn("Old Title", twice)
        self.assertIn("New Title", twice)


class TestValidation(unittest.TestCase):
    def test_valid_when_required_tags_present(self):
        result = inject_og_tags(SAMPLE_WITH_TITLE_H1, url="https://claude.ai/artifact/abc")
        report = validate_og_tags(result)
        self.assertTrue(report["valid"])
        self.assertEqual(report["issues"], [])

    def test_invalid_when_no_og_tags(self):
        report = validate_og_tags(SAMPLE_WITH_TITLE_H1)
        self.assertFalse(report["valid"])
        self.assertIn("missing og:title", report["issues"])
        self.assertIn("missing og:description", report["issues"])
        self.assertIn("missing og:type", report["issues"])

    def test_warns_but_still_valid_without_url(self):
        result = inject_og_tags(SAMPLE_WITH_TITLE_H1)
        report = validate_og_tags(result)
        self.assertTrue(report["valid"])
        self.assertIn("optional og:url not set", report["issues"])

    def test_invalid_when_content_empty(self):
        broken = '<head><meta property="og:title" content=""></head>'
        report = validate_og_tags(broken)
        self.assertFalse(report["valid"])
        self.assertIn("og:title is empty", report["issues"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
