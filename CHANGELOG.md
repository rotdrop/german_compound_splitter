# Changelog

Every release needs a `## [X.Y.Z]` (or `## [X.Y.Z-rcW]`) section here;
the release workflow fails otherwise.

## [Unreleased]

## [0.1.5] - 2026-10-28

### Fixed
- Accept valid `iconv` transliteration output even when `iconv` exits non-zero
  (#17, #18).

## [0.1.4] - 2026-10-27

### Added
- Locale-aware transliteration via `iconv`, with libc locale validation, so
  transliterated input (e.g. `Kapitaensmuetze`) can be split (#3, #4, #5, #7).
- Automatic output transliteration with locale detection and a
  `transliteration_locale` override for `dissect` (#10).
- `TransliteratingAutomaton` returned by `read_dictionary_from_file`.
- Ported upstream improvements (#1).
- GitHub Actions: tests on Python 3.13-3.15, Codecov upload, tag-triggered
  release workflow, automatic `CONTRIBUTORS.md` update (#6, #9, #11, #14).

### Changed
- Repository restructured to a `src` layout with `pyproject.toml` and an
  explicit package API (#8).
- README: upstream attribution and derived-work notice (#12, #13).
- Test coverage raised to 90% (#15).
