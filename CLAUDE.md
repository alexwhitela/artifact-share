# CLAUDE.md

This repo's only purpose is publishing individual artifact pages to GitHub
Pages so their links unfurl correctly in Slack. Every commit here is
already intended to end up on the public internet — that's the whole
point of the repo.

**Pre-authorized:** running `tools/publish_artifact.sh` (including the
`git add` / `git commit` / `git push` it performs) does not need a
separate confirmation each time — publishing via that script, with the
user's own invocation of it, is the confirmation.

**Not pre-authorized:** publishing content that looks sensitive — real
user data, unredacted financial figures, anything the user wouldn't
otherwise post publicly. If an artifact being published looks like it
might be that, flag it and confirm before running the script, same as any
other "publish publicly" action.

No build/lint/test tooling beyond `python3 tools/test_og_tags.py`.
