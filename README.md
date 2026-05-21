# 🏦 Banking Data Warehouse

An end-to-end, production-grade data warehouse built on Google Cloud Platform (GCP) for a retail banking domain. This project simulates real-world data engineering workflows — from raw data ingestion to analytics-ready dashboards.

---

## 🏗️ Architecture
┌─────────────────┐ ┌─────────────┐ ┌──────────────────┐ ┌─────────────────────┐ ┌───────────────┐
│ Data Simulator │────▶│ GCS Bucket │────▶│ BigQuery Staging │────▶│ BigQuery Warehouse │────▶│ Looker Studio │
│ (Python) │ │ (Raw CSVs) │ │ (Raw Tables) │ │ (Star Schema) │ │ (Dashboard) │
└─────────────────┘ └─────────────┘ └──────────────────┘ └─────────────────────┘ └───────────────┘
▲
─────────────────────────
│ Cloud Composer (Airflow) │
│ Orchestrates all steps │
─────────────────────────

---
## ⚙️ Tech Stack
| Tool | Purpose |
|---|---|
| Python | Data simulation and generation |
| Google Cloud Storage (GCS) | Raw data landing zone |
| BigQuery | Staging and warehouse layers |
| Cloud Composer (Airflow) | Pipeline orchestration |
| Terraform | Infrastructure as Code |
| Looker Studio | Business dashboards |
| GitHub Actions | CI/CD pipeline |
---

## 📁 Project Structure
banking-data-warehouse/
│
├── data/
│ └── simulator/
│ └── generate_data.py # Generates fake banking CSVs
│
├── infra/
│ └── terraform/
│ ├── main.tf # GCS + BigQuery infrastructure
│ ├── variables.tf # Configurable variables
│ └── outputs.tf # Output values after apply
│
├── bigquery/
│ ├── staging/
│ │ └── create_staging_tables.sql
│ └── warehouse/
│ ├── create_dim_tables.sql
│ └── create_fact_tables.sql
│
├── dags/
│ └── banking_etl_dag.py # Cloud Composer DAG
│
├── tests/
│ └── test_data_quality.py # Data quality checks
│
├── .github/
│ └── workflows/
│ └── ci.yml # CI/CD pipeline
│
└── README.md

---
## 📊 Data Model (Star Schema)
                ┌──────────────┐
                │ dim_customer │
                └──────┬───────┘
                       │
┌──────────────┐ ┌──────┴──────────────┐ ┌──────────────┐
│ dim_date │────│ fact_transactions │────│ dim_merchant │
└──────────────┘ └──────┬──────────────┘ └──────────────┘
│
┌──────┴───────┐
│ dim_account │
└──────────────┘

| Table | Type | Rows |
|---|---|---|
| fact_transactions | Fact | 500+ |
| dim_customer | Dimension | 100 |
| dim_account | Dimension | 100 |
| dim_merchant | Dimension | 50 |
| dim_date | Dimension | 1,826 |
---
## 🚀 How to Run
### 1. Clone the repository
```bash
git clone https://github.com/shree-basu/banking-data-warehouse.git
cd banking-data-warehouse
2. Install dependencies
pip install pandas faker
3. Generate data
python data/simulator/generate_data.py
4. Run data quality tests
python tests/test_data_quality.py
5. Deploy infrastructure (requires GCP account)
cd infra/terraform
terraform init
terraform plan
terraform apply

✅ Key Features
Realistic banking data — 500 transactions across 100 customers, 100 accounts, 50 merchants
ELT pattern — raw data lands in GCS, transformed inside BigQuery using SQL
Star schema — optimised for analytical queries with partitioning and clustering on fact_transactions
Automated orchestration — Cloud Composer DAG runs daily at 2AM, loading data from GCS to BigQuery
Data quality checks — row count, null, duplicate and value validity checks on every run
Infrastructure as Code — full GCP infrastructure defined in Terraform
CI/CD — GitHub Actions runs data quality tests on every push to main

📈 Pipeline Schedule
The DAG runs daily at 2:00 AM IST via Cloud Composer:
Load raw CSVs from GCS → BigQuery Staging (parallel)
Transform staging → dim_customer, dim_date, dim_merchant (parallel)
Transform staging → dim_account (after dim_customer)
Transform staging → fact_transactions (after all dims)
