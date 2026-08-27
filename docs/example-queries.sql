-- Replace {{project_id}} using scripts/bq_dry_run.py --project.
SELECT
  transaction_date,
  merchant_key,
  COUNT(*) AS transaction_count,
  SUM(amount) AS amount_total
FROM `{{project_id}}.curated.fact_transactions`
WHERE transaction_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) AND CURRENT_DATE()
GROUP BY transaction_date, merchant_key;

SELECT
  s.business_date,
  a.account_type,
  SUM(s.balance) AS ending_balance
FROM `{{project_id}}.curated.fact_account_daily_snapshot` AS s
JOIN `{{project_id}}.curated.dim_account` AS a
  ON s.account_key = a.account_key
 AND TIMESTAMP(s.business_date) >= a.effective_from
 AND TIMESTAMP(s.business_date) < a.effective_to
WHERE s.business_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
GROUP BY s.business_date, a.account_type;
