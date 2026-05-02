set dotenv-load := true

test:
    pytest

lint:
    ruff check .

format:
    ruff format .

typecheck:
    mypy pgloom

migrate:
    pgloom db migrate

scenario-smoke:
    pgloom scenario run scenarios/core/smoke
