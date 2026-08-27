# ADR 004: Conservative gated deployment

Status: accepted.

Terraform uses a bootstrapped versioned GCS backend, exact tool/provider pins, GitHub OIDC/WIF, and a manually approved deployment environment. Composer remains disabled by default. Deployment order is infrastructure, SQL, then DAG. Long-lived keys, automatic PR applies, unconditional destructive flags, and implicit Composer creation were rejected.
