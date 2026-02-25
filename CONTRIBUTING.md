# Contributing to AdversaryPilot

Thank you for your interest in contributing to AdversaryPilot! This guide will help you get started.

## Development Setup

```bash
git clone https://github.com/aviralsrivastava/AdversaryPilot.git
cd AdversaryPilot
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python 3.11+.

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=adversarypilot --cov-report=term-missing

# Run a specific test file
pytest tests/test_compliance_framework.py -v
```

All tests must pass before submitting a PR. Current target: 626+ tests.

## Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
ruff check src/ tests/
ruff format src/ tests/
```

Configuration is in `pyproject.toml`:
- Target: Python 3.11
- Line length: 100

## Type Checking

```bash
mypy src/adversarypilot/
```

Strict mode is enabled. All public APIs should have type annotations.

## Adding a New Technique

1. Add the technique entry to `src/adversarypilot/taxonomy/catalog.yaml` with all required fields (id, name, domain, phase, surface, access_levels, goals, cost, stealth_profile, execution_mode, atlas_refs, compliance_refs, tags, description)
2. Add benchmark priors to `src/adversarypilot/planner/priors.py` if the technique has published ASR data
3. Add tool mappings to `src/adversarypilot/hooks/generator.py` if garak/promptfoo support exists
4. Add tests in `tests/`
5. Update the technique count in `README.md`

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes with tests
4. Ensure all tests pass and linting is clean
5. Submit a PR with a clear description of the change

## Reporting Issues

Use [GitHub Issues](https://github.com/aviralsrivastava/AdversaryPilot/issues) for bug reports and feature requests. For security vulnerabilities, please use responsible disclosure — email the maintainer directly.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
