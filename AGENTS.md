# Repository agent guide

- Preserve immutable batch identity and audit evidence; never overwrite generated or cloud raw objects.
- Keep cloud deployment manual, WIF-based, and Composer opt-in. Do not apply infrastructure without explicit approval.
- Use Python 3.12 locally. Run `pytest -q`, `ruff check .`, `sqlfluff lint bigquery --dialect bigquery --rules CP01 --ignore-local-config`, and the DagBag test before handoff.
- Use Terraform 1.14.5 and provider 7.17.0. Run backend-disabled init, format check, and validate; never commit state, plans, credentials, or `.auto.tfvars`.
- Update the version matrix and evidence status when changing runtime pins or validation scope.
