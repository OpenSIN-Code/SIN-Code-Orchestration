# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial SIN-Code-Bundle integration (ceo-audit workflow v3)
- OpenCode MCP server registration under `OpenSIN-Code/SIN-Code-Orchestration`
- Repository-level `SIN_GITHUB_FALLBACK_TOKEN` secret for the App commenter fallback
- DAG-based multi-agent orchestration engine with parallel execution, retry, and verification
- Role coordination (developer, tester, architect) with dependency-aware scheduling
- Python 3.9+ support under the MIT license
- Installed via the [SIN-Code Bundle](https://github.com/OpenSIN-Code/SIN-Code-Bundle): `pip install sin-code-orchestration`

### Security
- All commits verified via `git-immortal-commit` (annotated tags)
- DAG validation rejects cycles before execution
