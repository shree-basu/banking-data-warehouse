import pandas as pd
import os

def test_file_exists():
    files = [
        'data/simulator/output/customers.csv',
        'data/simulator/output/accounts.csv',
        'data/simulator/output/merchants.csv',
        'data/simulator/output/dates.csv',
        'data/simulator/output/transactions.csv'
    ]
    for file in files:
        assert os.path.exists(file), f"Missing file: {file}"
    print("✓ All files exist")

def test_row_counts():
    customers = pd.read_csv('data/simulator/output/customers.csv')
    accounts = pd.read_csv('data/simulator/output/accounts.csv')
    merchants = pd.read_csv('data/simulator/output/merchants.csv')
    transactions = pd.read_csv('data/simulator/output/transactions.csv')

    assert len(customers) == 100, f"Expected 100 customers, got {len(customers)}"
    assert len(accounts) == 100, f"Expected 100 accounts, got {len(accounts)}"
    assert len(merchants) == 50, f"Expected 50 merchants, got {len(merchants)}"
    assert len(transactions) == 500, f"Expected 500 transactions, got {len(transactions)}"
    print("✓ Row counts are correct")

def test_no_nulls():
    transactions = pd.read_csv('data/simulator/output/transactions.csv')
    critical_columns = ['transaction_id', 'account_id', 'merchant_id', 'amount']
    for col in critical_columns:
        assert transactions[col].isnull().sum() == 0, f"Nulls found in {col}"
    print("✓ No nulls in critical columns")

def test_no_duplicates():
    transactions = pd.read_csv('data/simulator/output/transactions.csv')
    assert transactions['transaction_id'].duplicated().sum() == 0, "Duplicate transaction_ids found"
    print("✓ No duplicate transaction IDs")

def test_valid_status():
    transactions = pd.read_csv('data/simulator/output/transactions.csv')
    valid_statuses = ['Success', 'Failed', 'Pending']
    invalid = transactions[~transactions['status'].isin(valid_statuses)]
    assert len(invalid) == 0, f"Invalid status values found: {invalid['status'].unique()}"
    print("✓ All status values are valid")

if __name__ == '__main__':
    test_file_exists()
    test_row_counts()
    test_no_nulls()
    test_no_duplicates()
    test_valid_status()
    print("\n All data quality checks passed!")