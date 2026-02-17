# Quick Start Guide - Testing

## Running Your Tests

### Step 1: Activate Virtual Environment
```bash
cd D:\College\FinalProject\Final-project
.\venv\Scripts\activate
```

### Step 2: Run Tests
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py
pytest tests/test_task_service.py
```

### Step 3: View Coverage Report
After running with coverage, open: `htmlcov/index.html` in your browser

## What Was Created

### 📁 Directory Structure
```
tests/
├── __init__.py
├── conftest.py           # Test fixtures
├── test_auth.py          # 11 authentication tests
├── test_task_service.py  # 19 task service tests
└── README.md             # Detailed testing guide

app/
├── services/
│   ├── __init__.py
│   └── task_service.py   # Business logic layer
└── exceptions.py         # Custom exceptions
```

### ✅ Test Results
- **30 tests** created
- **All 30 passing** ✅
- **87% coverage** on task service
- **100% coverage** on exceptions

## Example Test Commands

```bash
# Quick test run
pytest

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run tests matching pattern
pytest -k "create"

# Run with full coverage report
pytest --cov=app --cov-report=html --cov-report=term-missing
```

## Test Categories

### Authentication Tests (test_auth.py)
- User model (password hashing, creation)
- Login/logout functionality
- Registration
- Protected routes
- Authorization

### Task Service Tests (test_task_service.py)
- Create tasks with validation
- Update task status
- Authorization checks
- Task filtering
- Delete tasks
- Update tasks

## Next Steps

1. **Run tests regularly** before commits
2. **Add more tests** for other features:
   - Flashcards
   - Summarizer
   - AI Planner
   - Google Calendar integration
3. **Maintain coverage** above 80%
4. **Update tests** when adding new features

## Documentation
- Detailed guide: `tests/README.md`
- Implementation summary: `TESTING.md`
- Configuration: `pytest.ini`

## Need Help?
- Check `tests/README.md` for detailed instructions
- See examples in existing test files
- Pytest docs: https://docs.pytest.org/
