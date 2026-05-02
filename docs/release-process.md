# Release Process

1. Update `CHANGELOG.md`: move unreleased entries under a dated release heading.
2. Bump `pyproject.toml` to the same version.
3. Commit with `release: X.Y.Z`.
4. Tag and push: `git tag vX.Y.Z && git push origin vX.Y.Z`.
5. Watch the release workflow:
   - `build`
   - `test-on-built-wheel`
   - `publish-testpypi`
   - `publish-pypi`, which blocks on the protected environment approval
   - `github-release`
6. Verify from a fresh environment: `pip install --upgrade pgloom && pgloom --help`.

Trusted Publishing is configured in PyPI and TestPyPI as a pending publisher for
`joshorig/pgloom`, workflow file `release.yml`, with GitHub environments named
`pypi` and `testpypi`.
