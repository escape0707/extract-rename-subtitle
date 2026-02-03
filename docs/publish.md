# Publishing to PyPI

This repo is prepared for publishing but not published by default.

## Steps

1. Choose a final PyPI name and ensure it is available.
2. Update `pyproject.toml` with the final name, version, and description.
3. Build the package:

   ```bash
   uv build
   ```

4. Upload to PyPI:

   ```bash
   uv publish
   ```

Consider using TestPyPI first.
