# Version matrix

| Component | Pin | Role / decision |
|---|---|---|
| Cloud Composer | `composer-3-airflow-2.10.5-build.47` | Hosted deployment target; Aug 2026 build selected for its Airflow 2.10 line, not simply newest |
| Apache Airflow | `2.10.5` | DAG API and upstream constraints baseline |
| Google Airflow provider | `17.1.0` hosted / `12.0.0` local CI | Composer image supplies 17.1.0; upstream Airflow 2.10.5 constraints supply 12.0.0 for portable DagBag parsing |
| Composer Python | `3.11.8` | Supplied by selected image |
| Local/CI Python | `3.12` | Supported by Airflow 2.10.5 upstream constraints |
| Terraform | `1.14.5` | Exact repository/toolchain pin |
| Google Terraform provider | `7.17.0` | Exact lock-file pin validated with Terraform 1.14.5 |

Primary references: [Composer versions](https://cloud.google.com/composer/docs/concepts/versioning/composer-versions), [Composer release notes](https://cloud.google.com/composer/docs/composer-versions), [Airflow constraints](https://airflow.apache.org/docs/apache-airflow/stable/installation/installing-from-pypi.html), [Terraform releases](https://releases.hashicorp.com/terraform/), and [Google provider releases](https://github.com/hashicorp/terraform-provider-google/releases).

The two provider pins are intentional. Composer images own a tested package set that differs from the upstream Airflow constraints. CI proves DAG compatibility against the upstream set; an authorized non-production Composer smoke test remains required before deployment promotion.
