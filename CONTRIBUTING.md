# Contributing to TSRKit Types

We welcome contributions! Here's how to get started.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/chainscore/tsrkit-types.git
   cd tsrkit-types
   ```

2. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

Run the full test suite:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=tsrkit_types --cov-report=html
```

Run tests in parallel (faster):
```bash
pytest -n auto
```

Run specific test files:
```bash
pytest tests/test_integers.py
pytest tests/test_strings.py
```

## Code Style

- Follow PEP 8
- Use type hints for all functions and methods
- Add docstrings for public APIs
- Keep functions focused and testable

## Submitting Changes

1. **Fork the repository** on GitHub
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and add tests
4. **Run the test suite** to ensure everything passes
5. **Commit your changes** with descriptive messages
6. **Push to your fork** and submit a pull request

## What to Contribute

- Bug fixes
- New data types or features
- Performance improvements
- Documentation improvements
- Test coverage improvements

## Questions?

Feel free to open an issue for discussion before starting work on major changes.

Thanks for contributing! 🚀 