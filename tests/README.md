# Testing Guide

This directory contains tests for the BrainDump application.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Shared fixtures and configuration
├── test_auth.py             # Authentication tests
└── test_task_service.py     # Task service tests
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/test_auth.py
pytest tests/test_task_service.py
```

### Run specific test class
```bash
pytest tests/test_auth.py::TestUserModel
pytest tests/test_task_service.py::TestTaskService
```

### Run specific test
```bash
pytest tests/test_auth.py::TestUserModel::test_password_hashing
```

### Run with coverage report
```bash
pytest --cov=app --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`

### Run with verbose output
```bash
pytest -v
```

### Run tests matching a pattern
```bash
pytest -k "auth"        # Run all tests with "auth" in their name
pytest -k "create"      # Run all tests with "create" in their name
```

## Test Fixtures

Common fixtures available in `conftest.py`:

- `app` - Flask application instance configured for testing
- `db_session` - Database session with clean state for each test
- `client` - Test client for making HTTP requests
- `test_user` - Pre-created test user
- `test_user_2` - Second test user for authorization tests
- `auth_client` - Authenticated test client
- `test_category` - Pre-created test category

## Writing New Tests

### Example: Testing a new service method

```python
def test_my_new_feature(db_session, test_user):
    """Test description"""
    # Arrange
    # ... setup test data
    
    # Act
    result = MyService.do_something(test_user.id)
    
    # Assert
    assert result is not None
    assert result.property == expected_value
```

### Example: Testing a route

```python
def test_new_route(auth_client):
    """Test new route"""
    response = auth_client.get('/new-route')
    
    assert response.status_code == 200
    assert b'Expected Content' in response.data
```

## Test Coverage

To view current test coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

## Continuous Integration

Tests should be run before:
- Committing code
- Creating pull requests
- Deploying to production

## Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
   - `test_create_task_success` ✓
   - `test_task` ✗

2. **Test Organization**: Group related tests in classes
   - `TestTaskService`
   - `TestAuthRoutes`

3. **Test Independence**: Each test should be independent and not rely on others

4. **Use Fixtures**: Reuse common setup using fixtures instead of duplicating code

5. **Test Edge Cases**: Test both success and failure scenarios
   - Valid input
   - Invalid input
   - Edge cases
   - Authorization failures

6. **Keep Tests Fast**: Unit tests should run quickly

## Troubleshooting

### Database Errors
If you see database errors, ensure the test database is being properly cleaned:
```python
# conftest.py handles this with db.drop_all()
```

### Import Errors
Make sure you're in the project root and the virtual environment is activated:
```bash
cd d:\College\FinalProject\Final-project
.\venv\Scripts\activate
```

### Fixture Not Found
Ensure `conftest.py` is in the tests directory and contains the fixture definition.

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing Documentation](https://flask.palletsprojects.com/en/latest/testing/)
- [pytest-flask Plugin](https://pytest-flask.readthedocs.io/)
