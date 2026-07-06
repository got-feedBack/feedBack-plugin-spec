# Contributing to the feedBack plugin specification

Thanks for helping evolve the feedBack plugin format. This repository holds a **specification** —
a contract that the feedBack Host and every plugin author rely on — so contributions are a little
different from a normal code project. The process below keeps the format stable and its history
clear.

## Licensing of contributions (inbound = outbound)

This repository is licensed under [**AGPL-3.0-only**](LICENSE). By opening a pull request you
agree your contribution is licensed under those same terms.

## Developer Certificate of Origin (DCO)

Every commit must be signed off, certifying you have the right to submit it under the license
above (see [developercertificate.org](https://developercertificate.org/)):

```bash
git commit -s -m "your message"
```

This appends a `Signed-off-by: Your Name <you@example.com>` trailer. If you forget, amend with
`git commit --amend -s` (or rebase to sign off earlier commits) and force-push your branch.

## Plugin Spec Enhancement Proposals

Anything that changes what a conformant plugin or Host must do goes through a lightweight proposal
so the discussion and rationale are recorded.

1. **Open an issue** using the *Plugin Spec Enhancement Proposal* template. Lead with a one- or
   two-sentence summary, then describe the problem, the proposed change to the manifest and/or
   loading behaviour, backward compatibility, and which version bump it implies (see below).
2. **Discuss.** A proposal is refined in the issue until it has a clear shape and rough consensus.
   Editorial fixes (typos, clarifications) skip this and can go straight to a PR.
3. **Land it as a PR** that updates, together:
   - the normative spec (`spec/plugin-spec-v1.md`),
   - the manifest schema (`schemas/plugin.schema.json`) when the manifest shape changes,
   - an example under `examples/` that exercises the change (and still validates),
   - the `[Unreleased]` section of `CHANGELOG.md`.

A PR that changes behaviour but touches only one of those is incomplete.

### Which version bump does my change need?

| Your change | Bump |
|---|---|
| New **optional** manifest key or loading behaviour older Hosts ignore | **MINOR** |
| Wording, clarification, fixed example, best-practice tweak | **PATCH** |
| Removes/renames/repurposes a required key, or changes existing semantics | **MAJOR** |

Prefer additive (minor) changes. If you find yourself proposing a major bump, check first whether
the goal can be met with a new optional key instead — that is almost always the better design.

When you do bump, the version string lives in a few places that **must** all match, and CI
enforces it (`tools/check_versions.py`): the spec header, the README version table, and the newest
`## [X.Y.Z]` heading in `CHANGELOG.md`. Update them together; the guard prints exactly which one is
out of step if you miss any.

## Workflow

- Never push directly to `main`. Branch, then open a PR against
  `got-feedback/feedBack-plugin-spec:main`.
- CI must pass: the schema is meta-checked, the example plugins are validated, the validator's
  tests run, and the docs site builds. Run them locally first:
  ```bash
  pip install -r requirements-dev.txt
  python -m pytest -q
  python -m ruff check tools/ tests/
  python tools/validate.py examples/minimal-plugin examples/full-plugin
  python tools/check_versions.py
  ```
- Keep commits scoped; short imperative subject, a body explaining *why*, and the `Signed-off-by`
  trailer.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Questions

Not sure whether something is a bug, a clarification, or a full proposal? Open an issue and ask —
much cheaper than guessing.
