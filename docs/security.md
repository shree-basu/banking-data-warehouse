# Security

The raw bucket enforces uniform bucket-level access, public-access prevention, versioning, and soft deletion. The runtime identity receives object viewer on raw data, data editor on the four warehouse datasets, and BigQuery job user at project scope. It has no service-account keys.

GitHub deployment uses OIDC and Workload Identity Federation restricted by the repository claim. Terraform creates the WIF binding and an explicit, reviewable set of product-scoped deployment roles only when WIF is enabled; it never grants Owner or Editor. A privileged bootstrap identity must perform the first reviewed apply. Organizations should further replace broad product-admin roles with custom roles after observing the exact required permissions.

CI has `contents: read` except the manual deploy job's `id-token: write`. Actions are pinned to commit SHAs. Obvious credential patterns are scanned, generated data/state/Airflow state are ignored, and no credentials belong in tfvars, backend configuration, repository variables, or artifacts. GitHub environment variables contain identifiers, not secrets.

Required repository administration remains external: enable a ruleset for `main`, require PRs, require the three CI jobs, block force pushes/deletions, require conversation resolution, and require approval on the `production` environment. This repository does not claim those controls are currently configured.
