# artifact-share

Static host for sharing individual Claude artifacts with working Slack
(and other) link unfurls.

## Why this exists

A `claude.ai/artifact/...` link always unfurls with a fixed generic
preview ("Claude Artifact — Try out Artifacts created by Claude users"),
regardless of the artifact's own `<title>` or any `description` passed at
publish time. That's true even for a page whose HTML already has correct
`og:title`/`og:description` tags — the server returns a fixed set of tags
for every artifact route. Confirmed by fetching the route with Slack's own
crawler user agent and inspecting the raw response.

This repo sidesteps that: it's a plain public static site (GitHub Pages),
so the HTML it serves — including whatever Open Graph tags are in it — is
exactly what Slack's crawler reads.

**Tradeoff:** anything published here is genuinely public — fetchable by
anyone with the URL, with no access control, and potentially
search-indexable (unlike claude.ai artifacts, which are access-controlled
and `noindex`). Don't publish anything here you wouldn't want public.

## Publish an artifact

```bash
tools/publish_artifact.sh path/to/artifact.html my-artifact-slug \
  --title "Q3 Revenue Dashboard" \
  --description "Revenue by product line for Q3, with drill-down by region."
```

This injects Open Graph tags (via `tools/og_tags.py`), writes the result to
`a/<slug>/index.html`, commits, and pushes. After ~30-60s for GitHub Pages
to redeploy, the printed URL —
`https://alexwhitela.github.io/artifact-share/a/<slug>/` — is ready to
paste into Slack.

`--title`/`--description` are optional: if omitted, they're pulled from the
HTML's `<title>`/`<h1>` and a first-sentence heuristic over the body text.
Pass `--no-push` to commit locally without pushing yet.

## Tool internals

`tools/og_tags.py` — inject/validate Open Graph meta tags in an HTML file.
Tests: `python3 tools/test_og_tags.py`.
