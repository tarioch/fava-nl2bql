# Contributing

`fava-nl2bql` is a [Fava](https://beancount.github.io/fava/) extension that translates natural-language
questions about a ledger into [BQL](https://beancount.github.io/docs/beancount_query_language.html) queries
and runs them, published to PyPI. User documentation is in `docs/` (built with Sphinx, hosted on Read the Docs).

## Layout

| Path | Content |
|---|---|
| `src/fava_nl2bql/extension.py` | the `FavaExtensionBase` subclass Fava loads (report page, endpoints) |
| `src/fava_nl2bql/translator.py` | natural language → BQL translation (the tuned model lives behind this) |
| `src/fava_nl2bql/templates/` | Jinja template for the extension's report page |
| `src/fava_nl2bql/FavaNl2Bql.js` | the extension's JS module (Fava loads `<ClassName>.js` next to the class) |
| `tests/fava_nl2bql/` | tests, mirroring the layout of `src` |
| `docs/` | user documentation, `docs/api` is generated at build time and git-ignored |
| `scripts/readme_captures.py` | regenerates the screenshots and the GIF in `docs/_static/` used by the README and docs |

## Setup

```bash
uv sync --locked --dev
```

Python 3.11 to 3.14 are supported and tested.

## Checks

CI runs the same commands, all of them have to pass:

```bash
uv run pre-commit run --all-files   # ruff, ruff format, mypy, uv-lock, zizmor, rst lint
uv run deptry src                   # imports vs declared dependencies
uv run pytest
uv run --group docs sphinx-build -W --keep-going -b html docs docs/_build   # documentation without warnings
uv build
```

Things that catch people out:

- `pre-commit run --all-files` only looks at files tracked by git. `git add` new files before running it, otherwise
  they are not checked (and CI then fails on them).
- mypy runs in the project environment (a local pre-commit hook calling `uv run mypy`), so it checks against the types
  of the installed packages. Stub packages (`types-*`) belong into the `dev` dependency group.
- deptry fails for an import that is only available transitively and for a declared dependency that is not used.
  Declare what you import in `pyproject.toml`, remove what you stop using.

## Code

- Type hints are required in `src` (mypy `disallow_untyped_defs`, tests are exempt).
- ruff selects `E4, E7, E9, F, B, I, S113, T20, UP` (see `pyproject.toml`), `ruff format` decides the formatting.
- Tests use synthetic ledgers and fixtures only: no real account numbers, balances or personal financial data,
  not even anonymized ones.

## Dependencies

- `uv.lock` is committed. Regenerate it with the uv version of the `uv-lock` pre-commit hook (`rev` in
  `.pre-commit-config.yaml`), a different uv version rewrites unrelated parts of the file:
  `uvx --from uv==<rev> uv lock`.
- Dependabot (`.github/dependabot.yml`) opens grouped PRs for minor and patch updates of Python packages weekly and
  for GitHub Actions monthly. Major updates come as separate PRs.

## Screenshots

The README's GIF and the screenshots in the docs are generated, not taken by hand. After a UI change, regenerate
them and commit the result:

```bash
uv sync --locked --dev --group screenshots
uv run playwright install chromium
uv run --group screenshots python scripts/readme_captures.py
```

The script runs Fava on `bean-example`'s synthetic ledger and replays answers recorded from the real model, so no
Ollama server is needed. When the model changes, re-record those answers with `ollama run` (see `RECORDED` in the
script).

## Network

- The only network call is `translator.py`'s call to a local Ollama server via the `ollama` package.
  Always pass `timeout=` to `Client(...)` — a stalled server must not block the request forever.
- Tests must not make real network calls: mock `fava_nl2bql.translator.Client` (see
  `tests/fava_nl2bql/test_translator.py`).

## Git and pull requests

- Branch off `master`, named `feature/…`, `bugfix/…` or `chore/…` (snake_case after the prefix). The prefix labels
  the PR (`.github/pr-labeler.yml`), and the label decides the category in the release notes (the shared
  `release-drafter.yml` of [tarioch/.github](https://github.com/tarioch/.github)).
- Commit subjects are imperative and start with a capital letter, the body explains why.
- Changes go through pull requests into `master` and are merged with a merge commit.

## CI and releases

`.github/workflows/build-publish.yml` runs `lint`, `test` (matrix), `build`, and on pushes to `master` and version tags
the publish jobs. Workflows use the least permissions they need, and every action is pinned to a commit SHA.

- Every push to `master` publishes a development version to TestPyPI.
- Release notes are drafted by release-drafter. Publishing the draft creates the tag `vX.Y.Z`, which publishes to PyPI.
- Publishing uses PyPI trusted publishing (OIDC) from the GitHub environments `testpypi` and `pypi`, there are no
  stored tokens.
- The version is derived from the git tags (uv-dynamic-versioning), so CI checks out the full history (`fetch-depth: 0`).
