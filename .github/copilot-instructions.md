Always use `make` commands. Fallback to `uv`. Do not use `python` or `python3` or `pip` directly.

```bash
make run              # Run the application
make check            # Run ruff + basedpyright + pre-commit
make test             # Run all tests
make test-single TEST=test_services.py  # Run specific test
make format           # Auto-format and fix linting issues
make package          # Build macOS .app bundle
```

Run `make check` before finishing a task and make sure all the checks pass.
