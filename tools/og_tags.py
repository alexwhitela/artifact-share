#!/usr/bin/env python3
"""
Inject Open Graph meta tags into a Claude artifact HTML page so link
unfurls (Slack, iMessage, etc.) show the artifact's real title and
summary instead of the generic "Claude Artifact" fallback.

Usage:
    python3 og_tags.py inject page.html -o page.og.html \
        [--title "My Artifact"] [--description "One sentence summary."] \
        [--url "https://claude.ai/artifact/..."]

    python3 og_tags.py validate page.og.html
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from html.parser import HTMLParser

OG_META_RE = re.compile(
    r'<meta\s+property=["\']og:[^"\']+["\'][^>]*>\s*', re.IGNORECASE
)
HEAD_OPEN_RE = re.compile(r"<head[^>]*>", re.IGNORECASE)
HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)
HTML_OPEN_RE = re.compile(r"<html[^>]*>", re.IGNORECASE)

SENTENCE_END_RE = re.compile(r"[.!?](\s|$)")
MAX_DESCRIPTION_LEN = 200


class _ContentExtractor(HTMLParser):
    """Pulls the first <title>, first <h1> text, meta description, and
    body text (for a fallback summary) out of an HTML document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.h1: str | None = None
        self.meta_description: str | None = None
        self.body_text_parts: list[str] = []

        self._in_title = False
        self._in_h1 = False
        self._skip_tags = {"script", "style"}
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "title" and self.title is None:
            self._in_title = True
        elif tag == "h1" and self.h1 is None:
            self._in_h1 = True
        elif tag == "meta" and self.meta_description is None:
            name = (attrs_d.get("name") or "").lower()
            if name == "description" and attrs_d.get("content"):
                self.meta_description = attrs_d["content"].strip()
        elif tag in self._skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False
        elif tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._in_title:
            self.title = (self.title or "") + data
        if self._in_h1:
            self.h1 = (self.h1 or "") + data
        if not self._in_title and not self._in_h1 and len(" ".join(self.body_text_parts)) < 2000:
            stripped = data.strip()
            if stripped:
                self.body_text_parts.append(stripped)


def _one_sentence_summary(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    match = SENTENCE_END_RE.search(text)
    sentence = text[: match.end()].strip() if match else text
    if len(sentence) > MAX_DESCRIPTION_LEN:
        sentence = sentence[: MAX_DESCRIPTION_LEN - 1].rstrip() + "…"
    return sentence


def extract_title_and_description(
    page_html: str,
    title_override: str | None = None,
    description_override: str | None = None,
) -> tuple[str, str]:
    extractor = _ContentExtractor()
    extractor.feed(page_html)

    title = (
        title_override
        or (extractor.title and extractor.title.strip())
        or (extractor.h1 and extractor.h1.strip())
        or "Untitled Artifact"
    )
    title = re.sub(r"\s+", " ", title).strip()

    if description_override:
        description = description_override
    elif extractor.meta_description:
        description = extractor.meta_description
    else:
        body_text = " ".join(extractor.body_text_parts)
        description = _one_sentence_summary(body_text) or (
            "An interactive artifact created with Claude."
        )

    return title, description


def build_og_block(
    title: str, description: str, og_type: str, url: str | None
) -> str:
    lines = [
        f'<meta property="og:title" content="{html.escape(title, quote=True)}">',
        f'<meta property="og:description" content="{html.escape(description, quote=True)}">',
        f'<meta property="og:type" content="{html.escape(og_type, quote=True)}">',
    ]
    if url:
        lines.append(f'<meta property="og:url" content="{html.escape(url, quote=True)}">')
    return "\n".join(lines) + "\n"


def inject_og_tags(
    page_html: str,
    title: str | None = None,
    description: str | None = None,
    og_type: str = "website",
    url: str | None = None,
) -> str:
    """Return page_html with a fresh set of og: meta tags in <head>.

    Any og: meta tags already present are stripped first, so this is
    idempotent — safe to re-run on a page that already has tags.
    """
    resolved_title, resolved_description = extract_title_and_description(
        page_html, title, description
    )
    og_block = build_og_block(resolved_title, resolved_description, og_type, url)

    cleaned = OG_META_RE.sub("", page_html)

    head_open = HEAD_OPEN_RE.search(cleaned)
    if head_open:
        insert_at = head_open.end()
        return cleaned[:insert_at] + "\n" + og_block + cleaned[insert_at:]

    html_open = HTML_OPEN_RE.search(cleaned)
    if html_open:
        insert_at = html_open.end()
        return (
            cleaned[:insert_at]
            + f"\n<head>\n{og_block}</head>\n"
            + cleaned[insert_at:]
        )

    # No <html>/<head> at all — prepend a minimal head.
    return f"<head>\n{og_block}</head>\n" + cleaned


def validate_og_tags(page_html: str) -> dict:
    """Check presence and non-empty content of required OG tags.

    Returns a report dict: {"valid": bool, "tags": {...}, "issues": [...]}
    """
    required = {"og:title", "og:description", "og:type"}
    optional = {"og:url"}
    found: dict[str, str] = {}

    for match in re.finditer(
        r'<meta\s+property=["\']([^"\']+)["\']\s+content=["\']([^"\']*)["\'][^>]*>',
        page_html,
        re.IGNORECASE,
    ):
        prop, content = match.group(1).lower(), match.group(2)
        if prop.startswith("og:"):
            found[prop] = html.unescape(content)

    issues = []
    for prop in required:
        if prop not in found:
            issues.append(f"missing {prop}")
        elif not found[prop].strip():
            issues.append(f"{prop} is empty")

    for prop in optional:
        if prop not in found:
            issues.append(f"optional {prop} not set")

    return {
        "valid": all(not i.startswith("missing") and not i.endswith("empty") for i in issues)
        and all(r in found for r in required),
        "tags": found,
        "issues": issues,
    }


def _cmd_inject(args: argparse.Namespace) -> int:
    with open(args.input, "r", encoding="utf-8") as f:
        source = f.read()

    result = inject_og_tags(
        source,
        title=args.title,
        description=args.description,
        og_type=args.type,
        url=args.url,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Wrote {args.output}")
    else:
        print(result)
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    with open(args.input, "r", encoding="utf-8") as f:
        source = f.read()

    report = validate_og_tags(source)
    print(f"Valid: {report['valid']}")
    for prop, content in report["tags"].items():
        print(f"  {prop} = {content!r}")
    for issue in report["issues"]:
        prefix = "WARN" if issue.startswith("optional") else "FAIL"
        print(f"  [{prefix}] {issue}")
    return 0 if report["valid"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    inject_p = sub.add_parser("inject", help="Add/refresh OG meta tags in an HTML file")
    inject_p.add_argument("input", help="Path to the artifact HTML file")
    inject_p.add_argument("-o", "--output", help="Write result here instead of stdout")
    inject_p.add_argument("--title", help="Override the detected title")
    inject_p.add_argument("--description", help="Override the detected one-sentence summary")
    inject_p.add_argument("--type", default="website", help="og:type value (default: website)")
    inject_p.add_argument("--url", help="og:url value (the published artifact link)")
    inject_p.set_defaults(func=_cmd_inject)

    validate_p = sub.add_parser("validate", help="Check an HTML file's OG tags")
    validate_p.add_argument("input", help="Path to the HTML file to check")
    validate_p.set_defaults(func=_cmd_validate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
