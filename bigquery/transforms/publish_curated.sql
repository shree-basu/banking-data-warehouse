-- Procedures are called only after manifest, staging DQ, and reconciliation pass.
CREATE OR REPLACE PROCEDURE `curated.publish_dim_customer`(
  p_batch_id STRING,
  p_business_date DATE,
  p_source_table STRING,
  p_source_file STRING
)
BEGIN
  EXECUTE IMMEDIATE FORMAT("""
    CREATE TEMP TABLE source_customer AS
    SELECT
      *,
      TO_HEX(SHA256(CONCAT(
        COALESCE(name, ''), '|', CAST(age AS STRING), '|', COALESCE(gender, ''), '|',
        COALESCE(city, ''), '|', COALESCE(state, ''), '|', COALESCE(email, ''), '|',
        COALESCE(phone, ''), '|', kyc_status
      ))) AS hash_diff
    FROM `%s`
  """, p_source_table);

  BEGIN TRANSACTION;
    UPDATE `curated.dim_customer` AS target
    SET effective_to = p_business_date, is_current = FALSE
    WHERE target.is_current
      AND target.customer_key != '0'
      AND EXISTS (
        SELECT 1 FROM source_customer AS source
        WHERE source.customer_id = target.customer_id
          AND source.hash_diff != target.hash_diff
      );

    INSERT INTO `curated.dim_customer`
    SELECT
      TO_HEX(SHA256(CONCAT(source.customer_id, '|', CAST(p_business_date AS STRING)))),
      source.customer_id, source.name, source.age, source.gender, source.city,
      source.state, source.email, source.phone, source.kyc_status,
      source.customer_since, p_business_date, DATE '9999-12-31', TRUE,
      source.hash_diff, p_batch_id, p_source_file, CURRENT_TIMESTAMP()
    FROM source_customer AS source
    WHERE NOT EXISTS (
      SELECT 1 FROM `curated.dim_customer` AS target
      WHERE target.customer_id = source.customer_id
        AND target.is_current
        AND target.hash_diff = source.hash_diff
    );
  COMMIT TRANSACTION;
END;

CREATE OR REPLACE PROCEDURE `curated.publish_dim_account`(
  p_batch_id STRING,
  p_business_date DATE,
  p_source_table STRING,
  p_source_file STRING
)
BEGIN
  EXECUTE IMMEDIATE FORMAT("""
    CREATE TEMP TABLE source_account AS
    SELECT
      *,
      TO_HEX(SHA256(CONCAT(
        customer_id, '|', account_type, '|', currency, '|',
        COALESCE(branch_code, ''), '|', COALESCE(ifsc_code, ''), '|', status
      ))) AS hash_diff
    FROM `%s`
  """, p_source_table);

  BEGIN TRANSACTION;
    UPDATE `curated.dim_account` AS target
    SET effective_to = p_business_date, is_current = FALSE
    WHERE target.is_current
      AND target.account_key != '0'
      AND EXISTS (
        SELECT 1 FROM source_account AS source
        WHERE source.account_id = target.account_id
          AND source.hash_diff != target.hash_diff
      );

    INSERT INTO `curated.dim_account`
    SELECT
      TO_HEX(SHA256(CONCAT(source.account_id, '|', CAST(p_business_date AS STRING)))),
      source.account_id, source.customer_id, source.account_type, source.currency,
      source.branch_code, source.ifsc_code, source.opened_date, source.status,
      p_business_date, DATE '9999-12-31', TRUE, source.hash_diff,
      p_batch_id, p_source_file, CURRENT_TIMESTAMP()
    FROM source_account AS source
    WHERE NOT EXISTS (
      SELECT 1 FROM `curated.dim_account` AS target
      WHERE target.account_id = source.account_id
        AND target.is_current
        AND target.hash_diff = source.hash_diff
    );
  COMMIT TRANSACTION;
END;

CREATE OR REPLACE PROCEDURE `curated.publish_dim_merchant`(
  p_batch_id STRING,
  p_business_date DATE,
  p_source_table STRING,
  p_source_file STRING
)
BEGIN
  EXECUTE IMMEDIATE FORMAT("""
    CREATE TEMP TABLE source_merchant AS
    SELECT
      *,
      TO_HEX(SHA256(CONCAT(
        COALESCE(merchant_name, ''), '|', category, '|', COALESCE(city, ''), '|',
        COALESCE(state, ''), '|', status
      ))) AS hash_diff
    FROM `%s`
  """, p_source_table);

  BEGIN TRANSACTION;
    UPDATE `curated.dim_merchant` AS target
    SET effective_to = p_business_date, is_current = FALSE
    WHERE target.is_current
      AND target.merchant_key != '0'
      AND EXISTS (
        SELECT 1 FROM source_merchant AS source
        WHERE source.merchant_id = target.merchant_id
          AND source.hash_diff != target.hash_diff
      );

    INSERT INTO `curated.dim_merchant`
    SELECT
      TO_HEX(SHA256(CONCAT(source.merchant_id, '|', CAST(p_business_date AS STRING)))),
      source.merchant_id, source.merchant_name, source.category, source.city,
      source.state, source.registered_since, source.status, p_business_date,
      DATE '9999-12-31', TRUE, source.hash_diff, p_batch_id, p_source_file,
      CURRENT_TIMESTAMP()
    FROM source_merchant AS source
    WHERE NOT EXISTS (
      SELECT 1 FROM `curated.dim_merchant` AS target
      WHERE target.merchant_id = source.merchant_id
        AND target.is_current
        AND target.hash_diff = source.hash_diff
    );
  COMMIT TRANSACTION;
END;

CREATE OR REPLACE PROCEDURE `curated.publish_facts`(
  p_batch_id STRING,
  p_business_date DATE,
  p_transaction_table STRING,
  p_snapshot_table STRING,
  p_transaction_file STRING,
  p_snapshot_file STRING
)
BEGIN
  EXECUTE IMMEDIATE FORMAT(
    "CREATE TEMP TABLE source_transaction AS SELECT * FROM `%s`",
    p_transaction_table
  );
  EXECUTE IMMEDIATE FORMAT(
    "CREATE TEMP TABLE source_snapshot AS SELECT * FROM `%s`",
    p_snapshot_table
  );
  ASSERT (
    SELECT COUNT(*) = COUNT(DISTINCT transaction_id) FROM source_transaction
  ) AS 'transaction_id must be unique before MERGE';

  MERGE `curated.fact_transactions` AS target
  USING (
    SELECT
      source.transaction_id,
      source.account_id,
      source.merchant_id,
      COALESCE(customer.customer_key, '0') AS customer_key,
      COALESCE(account.account_key, '0') AS account_key,
      COALESCE(merchant.merchant_key, '0') AS merchant_key,
      CAST(FORMAT_DATE('%Y%m%d', DATE(source.transaction_ts)) AS INT64) AS date_key,
      source.transaction_ts,
      DATE(source.transaction_ts) AS transaction_date,
      source.amount, source.currency, source.channel, source.transaction_type,
      source.status, source.ip_address, source.country_code
    FROM source_transaction AS source
    LEFT JOIN `curated.dim_account` AS account
      ON source.account_id = account.account_id
      AND DATE(source.transaction_ts) >= account.effective_from
      AND DATE(source.transaction_ts) < account.effective_to
    LEFT JOIN `curated.dim_customer` AS customer
      ON account.customer_id = customer.customer_id
      AND DATE(source.transaction_ts) >= customer.effective_from
      AND DATE(source.transaction_ts) < customer.effective_to
    LEFT JOIN `curated.dim_merchant` AS merchant
      ON source.merchant_id = merchant.merchant_id
      AND DATE(source.transaction_ts) >= merchant.effective_from
      AND DATE(source.transaction_ts) < merchant.effective_to
  ) AS source
  ON target.transaction_id = source.transaction_id
  WHEN NOT MATCHED THEN
    INSERT (
      transaction_id, account_id, merchant_id, customer_key, account_key,
      merchant_key, date_key, transaction_ts, transaction_date, amount, currency,
      channel, transaction_type, status, ip_address, country_code, batch_id,
      source_file, loaded_at
    )
    VALUES (
      source.transaction_id, source.account_id, source.merchant_id,
      source.customer_key, source.account_key, source.merchant_key, source.date_key,
      source.transaction_ts, source.transaction_date, source.amount, source.currency,
      source.channel, source.transaction_type, source.status, source.ip_address,
      source.country_code, p_batch_id, p_transaction_file, CURRENT_TIMESTAMP()
    );

  MERGE `curated.fact_account_daily_snapshot` AS target
  USING (
    SELECT
      source.*,
      COALESCE(account.account_key, '0') AS account_key
    FROM source_snapshot AS source
    LEFT JOIN `curated.dim_account` AS account
      ON source.account_id = account.account_id
      AND source.business_date >= account.effective_from
      AND source.business_date < account.effective_to
  ) AS source
  ON target.account_id = source.account_id
    AND target.business_date = source.business_date
  WHEN NOT MATCHED THEN
    INSERT (
      account_key, account_id, business_date, balance, currency,
      batch_id, source_file, loaded_at
    )
    VALUES (
      source.account_key, source.account_id, source.business_date,
      source.balance, source.currency, p_batch_id, p_snapshot_file,
      CURRENT_TIMESTAMP()
    );
END;

CREATE OR REPLACE PROCEDURE `curated.repair_late_account_keys`(p_business_date DATE)
BEGIN
  UPDATE `curated.fact_transactions` AS fact
  SET
    account_key = account.account_key,
    customer_key = COALESCE(customer.customer_key, '0')
  FROM `curated.dim_account` AS account
  LEFT JOIN `curated.dim_customer` AS customer
    ON account.customer_id = customer.customer_id
    AND p_business_date >= customer.effective_from
    AND p_business_date < customer.effective_to
  WHERE fact.transaction_date = p_business_date
    AND fact.account_key = '0'
    AND fact.account_id = account.account_id
    AND fact.transaction_date >= account.effective_from
    AND fact.transaction_date < account.effective_to;
END;
