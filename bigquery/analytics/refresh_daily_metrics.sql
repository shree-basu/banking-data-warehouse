-- A batch-refreshed aggregate is used instead of a materialized view because
-- effective-dated dimension joins are central to this query and are deliberately
-- kept out of the materialized-view compatibility boundary.
CREATE TABLE IF NOT EXISTS `analytics.daily_transaction_metrics` (
  transaction_date DATE NOT NULL,
  account_type STRING NOT NULL,
  merchant_category STRING NOT NULL,
  channel STRING NOT NULL,
  transaction_count INT64 NOT NULL,
  successful_count INT64 NOT NULL,
  transaction_amount NUMERIC NOT NULL,
  successful_amount NUMERIC NOT NULL,
  refreshed_at TIMESTAMP NOT NULL
)
PARTITION BY transaction_date
CLUSTER BY account_type, merchant_category
OPTIONS (
  description = 'Batch-refreshed daily transaction counts and exact monetary totals',
  require_partition_filter = TRUE
);

CREATE OR REPLACE PROCEDURE `analytics.refresh_daily_transaction_metrics`(
  p_business_date DATE
)
BEGIN
  DELETE FROM `analytics.daily_transaction_metrics`
  WHERE transaction_date = p_business_date;

  INSERT INTO `analytics.daily_transaction_metrics`
  SELECT
    fact.transaction_date,
    COALESCE(account.account_type, 'Unknown'),
    COALESCE(merchant.category, 'Unknown'),
    fact.channel,
    COUNT(*),
    COUNTIF(fact.status = 'Success'),
    SUM(fact.amount),
    SUM(IF(fact.status = 'Success', fact.amount, 0)),
    CURRENT_TIMESTAMP()
  FROM `curated.fact_transactions` AS fact
  LEFT JOIN `curated.dim_account` AS account
    ON fact.account_key = account.account_key
  LEFT JOIN `curated.dim_merchant` AS merchant
    ON fact.merchant_key = merchant.merchant_key
  WHERE fact.transaction_date = p_business_date
  GROUP BY fact.transaction_date, account.account_type, merchant.category, fact.channel;
END;
