CREATE OR REPLACE PROCEDURE `audit.assert_curated_quality`(
  p_batch_id STRING,
  p_business_date DATE
)
BEGIN
  INSERT INTO `audit.dq_result`
  WITH rules AS (
    SELECT
      'ONE_CURRENT_CUSTOMER' AS rule_code,
      'dim_customer' AS entity,
      COUNT(*) AS failures
    FROM (
      SELECT customer_id
      FROM `curated.dim_customer`
      WHERE customer_key != '0'
      GROUP BY customer_id
      HAVING COUNTIF(is_current) != 1
    )
    UNION ALL
    SELECT 'ONE_CURRENT_ACCOUNT', 'dim_account', COUNT(*)
    FROM (
      SELECT account_id
      FROM `curated.dim_account`
      WHERE account_key != '0'
      GROUP BY account_id
      HAVING COUNTIF(is_current) != 1
    )
    UNION ALL
    SELECT 'ONE_CURRENT_MERCHANT', 'dim_merchant', COUNT(*)
    FROM (
      SELECT merchant_id
      FROM `curated.dim_merchant`
      WHERE merchant_key != '0'
      GROUP BY merchant_id
      HAVING COUNTIF(is_current) != 1
    )
    UNION ALL
    SELECT 'NON_OVERLAPPING_SCD', 'all_dimensions', COUNT(*)
    FROM (
      SELECT customer_id AS natural_key, effective_from, effective_to,
             LEAD(effective_from) OVER (
               PARTITION BY customer_id ORDER BY effective_from
             ) AS next_start
      FROM `curated.dim_customer`
      WHERE customer_key != '0'
      UNION ALL
      SELECT account_id, effective_from, effective_to,
             LEAD(effective_from) OVER (
               PARTITION BY account_id ORDER BY effective_from
             )
      FROM `curated.dim_account`
      WHERE account_key != '0'
      UNION ALL
      SELECT merchant_id, effective_from, effective_to,
             LEAD(effective_from) OVER (
               PARTITION BY merchant_id ORDER BY effective_from
             )
      FROM `curated.dim_merchant`
      WHERE merchant_key != '0'
    )
    WHERE next_start IS NOT NULL AND effective_to > next_start
    UNION ALL
    SELECT 'POSITIVE_TRANSACTION_AMOUNT', 'fact_transactions', COUNT(*)
    FROM `curated.fact_transactions`
    WHERE transaction_date = p_business_date AND amount <= 0
    UNION ALL
    SELECT 'ORPHAN_FACT_KEYS', 'fact_transactions', COUNT(*)
    FROM `curated.fact_transactions`
    WHERE transaction_date = p_business_date
      AND (customer_key IS NULL OR account_key IS NULL OR merchant_key IS NULL)
  )
  SELECT
    p_batch_id, p_business_date, rule_code, entity, 'ERROR',
    failures = 0, CAST(failures AS STRING), '0', CURRENT_TIMESTAMP()
  FROM rules;

  ASSERT (
    SELECT COUNTIF(NOT passed) = 0
    FROM `audit.dq_result`
    WHERE batch_id = p_batch_id AND severity = 'ERROR'
  ) AS 'curated data-quality gate failed';
END;

CREATE OR REPLACE PROCEDURE `audit.reconcile_batch`(
  p_batch_id STRING,
  p_business_date DATE
)
BEGIN
  DECLARE source_count INT64;
  DECLARE source_total NUMERIC;
  DECLARE curated_count INT64;
  DECLARE curated_total NUMERIC;
  SET (source_count, source_total) = (
    SELECT AS STRUCT source_row_count, source_monetary_total
    FROM `audit.batch_run`
    WHERE batch_id = p_batch_id
  );
  SET curated_count = (
    SELECT COUNT(*) FROM `curated.fact_transactions`
    WHERE transaction_date = p_business_date AND batch_id = p_batch_id
  );
  SET curated_total = (
    SELECT COALESCE(SUM(amount), 0) FROM `curated.fact_transactions`
    WHERE transaction_date = p_business_date AND batch_id = p_batch_id
  );

  UPDATE `audit.batch_run`
  SET curated_row_count = curated_count,
      curated_monetary_total = curated_total
  WHERE batch_id = p_batch_id;

  INSERT INTO `audit.dq_result`
  VALUES
    (
      p_batch_id, p_business_date, 'ROW_COUNT_RECONCILIATION',
      'fact_transactions', 'ERROR', source_count = curated_count,
      CAST(curated_count AS STRING), CAST(source_count AS STRING),
      CURRENT_TIMESTAMP()
    ),
    (
      p_batch_id, p_business_date, 'MONETARY_RECONCILIATION',
      'fact_transactions', 'ERROR', source_total = curated_total,
      CAST(curated_total AS STRING), CAST(source_total AS STRING),
      CURRENT_TIMESTAMP()
    );

  ASSERT source_count = curated_count
    AS 'final row-count reconciliation failed';
  ASSERT source_total = curated_total
    AS 'final monetary reconciliation failed';
END;
