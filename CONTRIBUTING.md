# Contributing

This is a release, not an actively-maintained product. The maintainer publishes their own books with this toolkit and is happy to merge fixes — but is not promising ongoing support, feature requests, or fast review.

That said, contributions are welcome if they:

1. **Fix a real bug** — open an issue first describing the bug, the manuscript it happened on (or a minimal reproducer), and what the expected behavior was.
2. **Parameterize a book-specific pattern** — if you find a hardcoded value that should be configurable, a PR that adds the CLI flag (with sensible default) is welcome.
3. **Add a KDP validator check** — KDP's rules evolve. If you discover a new failure mode KDP rejects on (and confirm it via an actual rejection email), a PR adding the check to `validate_*.py` is welcome.
4. **Improve the docs** — clarifications, typos, missing edge cases, additional examples. Open a PR directly.

Contributions that will likely be declined:

- **Major rewrites** — this is a working toolkit, not a framework. Major refactors that change the public CLI surface will not be accepted.
- **Adding heavy dependencies** — this toolkit deliberately uses only `pypdf`, `Pillow`, `python-docx`, plus the `pandoc` system binary. PRs adding LaTeX, Docker, or large frameworks will be declined.
- **Pretty UI / web interface** — the project is intentionally CLI-only. A web app on top is welcome as a SEPARATE project that depends on this one.
- **Marketing / discovery tooling** — Amazon ads, Goodreads scrapers, sales analytics belong in different repos.

## Style

- Python 3.10+
- Stay readable — no clever one-liners that future-you (or future-someone) can't decode
- Add a docstring to every function that does non-trivial work
- If you add a CLI flag, document it in the relevant `docs/*.md`
- Match the existing argparse style (long-form flags only: `--input`, not `-i`)

## Testing

There is no formal test suite. The toolkit is validated against real book productions. If you fix a bug, include in the PR description:

- The minimal manuscript snippet that reproduced the bug (or describe the structure)
- The error message you saw
- A description of what your fix does

## License

By contributing, you agree your contribution is licensed under the same MIT license as the rest of the repository.
