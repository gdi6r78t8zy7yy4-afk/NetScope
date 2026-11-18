# Contributing to NetScope

Thank you for your interest in contributing to NetScope! This document provides guidelines for contributors.

## Code of Conduct

- Be respectful and inclusive
- Focus on what is best for the community
- Show empathy towards other community members

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected behavior
   - Screenshots if applicable

### Suggesting Features

1. Search existing feature requests
2. Create a new issue with:
   - Feature description
   - Use case
   - Possible implementation approach

### Contributing Code

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest backend/app/tests/`)
5. Commit with clear messages
6. Push your branch and create a Pull Request

## Development Setup

### Prerequisites
- Python 3.12+
- Node.js 20+
- Rust (for desktop)
- macOS 13+

### Quick Start
```bash
./scripts/setup.sh
```

### Running Tests

#### Backend
```bash
cd backend
source venv/bin/activate
pytest app/tests/
```

#### Frontend
```bash
cd frontend
npm test
```

### Code Style

#### Python (Backend)
- Follow PEP 8 guidelines
- Use Black for formatting
- Run linter: `ruff check .`

#### TypeScript (Frontend)
- Follow Airbnb style guide
- Use ESLint and Prettier

#### Rust (Desktop)
- Follow rustfmt style

## Pull Request Process

1. Update README.md if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Update documentation as needed
5. Request review from maintainers

## Commit Message Guidelines

Use the following format:
```
type: description

- type: feat | fix | docs | style | refactor | test | chore
- description: concise summary of changes

Example:
feat: add port scanning functionality
```

## Questions?

Open an issue or contact the maintainers.

---

Thank you for contributing to NetScope!
