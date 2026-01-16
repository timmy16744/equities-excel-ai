# Contributing to Equities AI

Thank you for your interest in contributing to Equities AI.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment (see README.md)
4. Create a branch for your changes

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/equities-excel-ai.git
cd equities-excel-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start infrastructure
cd docker && docker-compose up -d && cd ..

# Run backend
uvicorn backend.api.main:app --reload

# Run frontend (new terminal)
cd frontend && python server.py
```

## Code Style

### Python
- Follow PEP 8 guidelines
- Use type hints for function signatures
- Format with `black`
- Lint with `ruff`
- Type check with `mypy`

```bash
black backend/
ruff check backend/
mypy backend/
```

### JavaScript
- Use modern ES6+ syntax
- Keep functions small and focused
- Document complex logic with comments

### CSS
- Follow BEM naming convention where appropriate
- Keep selectors specific but not overly complex

## Commit Messages

Write clear, concise commit messages:

- Use imperative mood ("Add feature" not "Added feature")
- Keep the first line under 72 characters
- Reference issues when applicable

Examples:
```
Add new sentiment analysis agent
Fix WebSocket reconnection logic
Update API documentation for settings endpoints
```

## Pull Request Process

1. **Create a branch** from `main` with a descriptive name
   - `feature/add-new-agent`
   - `fix/websocket-timeout`
   - `docs/update-installation`

2. **Make your changes** with clear, atomic commits

3. **Test your changes**
   ```bash
   pytest tests/ -v
   ```

4. **Update documentation** if needed

5. **Submit a PR** with:
   - Clear description of changes
   - Reference to related issues
   - Screenshots for UI changes

## Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest --cov=backend tests/

# Specific test file
pytest tests/unit/test_agents.py -v
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Name test files with `test_` prefix
- Use descriptive test function names

## Reporting Issues

When reporting issues, please include:

1. **Description** of the problem
2. **Steps to reproduce**
3. **Expected behavior**
4. **Actual behavior**
5. **Environment** (OS, Python version, browser)
6. **Logs** if applicable

## Feature Requests

For feature requests:

1. Check existing issues first
2. Describe the use case
3. Explain why it would be valuable
4. Consider implementation approach

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Assume good intentions

## Questions?

Open an issue with the `question` label for any questions about contributing.
