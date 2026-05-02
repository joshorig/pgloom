# Scenario Harness

Scenarios are YAML files with ordered `steps` and simple `assertions`. The initial harness uses
fake handlers and Postgres state so smoke and regression scenarios avoid live external services.

Run:

```bash
pgloom scenario run scenarios/core/smoke
```
