# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- Pre-commit hooks to validate contracts and run contract tests.
- GitHub Actions workflow to validate and test contracts on PRs.
### Changed
- Validator now enforces `$schema` as first key and treats warnings as errors (with small allowlist).
- Dependencies pinned for jsonschema/pytest/pre-commit.
