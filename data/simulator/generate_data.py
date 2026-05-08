import pandas as pd
import random
import uuid
from faker import Faker
from datetime import datetime, timedelta
import os

fake = Faker('en_IN')
random.seed(42)

def generate_customers(n=100):
    customers = []
    for _ in range(n):
        customers.append({
            'customer_id': str(uuid.uuid4()),
            'name': fake.name(),
            'age': random.randint(21,65),
            'gender': random.choice(['Male', 'Female']),
            'city': fake.city(),
            'state': fake.state(),
            'email': fake.email(),
            'phone': fake.phone_number(),
            'kyc_status': random.choice(['Verified', 'Pending', 'Rejected']),
            'customer_since': fake.date_between(
                start_date = '-5y', end_date = 'today'
            ).strftime('%Y-%m-%d')
        })
    return pd.DataFrame(customers)
    
def generate_accounts(customer_ids, n=100):
    account_types = ['Savings', 'Current', 'Fixed Deposit', 'Recurring Deposit']
    accounts =[]
    for _ in range(n):
        accounts.append({
            'account_id': str(uuid.uuid4()),
            'customer_id': random.choice(customer_ids),
            'account_type': random.choice(account_types),
            'balance': round(random.uniform(1000,500000),2),
            'currency': 'INR',
            'branch_code': fake.bothify(text = 'BR###'),
            'ifsc_code': fake.bothify(text='????0######'),
            'opened_date': fake.date_between(
                start_date = '-5y', end_date = 'today'
            ).strftime('%Y-%m-%d'),
            'status': random.choice(['Active', 'Inactive', 'Frozen'])
        })
    return pd.DataFrame(accounts)
    
def generate_merchants(n=50):
    categories = ['Food & Dining', 'Travel', 'Healthcare', 'Retail', 'Education','Utilities','Entertainment']
    merchants = []
    for _ in range(n):
        merchants.append({
            'merchant_id' : str(uuid.uuid4()),
            'merchant_name': fake.company(),
            'category': random.choice(categories),
            'city': fake.city(),
            'state': fake.state(),
            'registered_since': fake.date_between(
                start_date = '-10y', end_date = 'today'
            ).strftime('%Y-%m-%d'),
            'status': random.choice(['Active','Inactive'])
        })
    return pd.DataFrame(merchants)

def generate_dates(start_date = '2020-01-01', end_date = '2024-12-31'):
    dates = []
    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    while current <= end:
        dates.append({
            'date_id': current.strftime('%Y%m%d'),
            'full_date': current.strftime('%Y-%m-%d'),
            'day': current.day,
            'month': current.month,
            'month_name': current.strftime('%B'),
            'quarter': (current.month -1)//3 + 1,
            'day_of_week': current.strftime('%A'),
            'is_weekend': current.weekday()>= 5
        })
        current += timedelta(days=1)
    return pd.DataFrame(dates)

def generate_transactions(account_ids, merchant_ids, date_ids, n=500):
    channels = ['ATM', 'Mobile App', 'Internet Banking', 'Branch']
    transactions = []
    for _ in range(n):
        transactions.append({
          'transaction_id': str(uuid.uuid4()),
          'account_id': random.choice(account_ids),
           'merchant_id': random.choice(merchant_ids),
           'date_id': random.choice(date_ids),
           'amount': round(random.uniform(100,100000),2),
           'currency': 'INR',
           'channel': random.choice(channels),
           'transaction_type': random.choice(['Debit','Credit']),
           'status': random.choice(['Success', 'Failed', 'Pending']),
           'ip_address': fake.ipv4() if random.random()> 0.3 else None,
           'country_code': random.choice(['IN','US','GB','AE','SG'])
        })
    return pd.DataFrame(transactions)
    
def main():
    output_dir = 'data/simulator/output'
    os.makedirs(output_dir, exist_ok= True)

    print("Generating customers...")
    customers_df = generate_customers(100)

    print("Generating accounts...")
    accounts_df = generate_accounts(
        customers_df['customer_id'].tolist(),100)
    
    print("Generating merchants...")
    merchants_df = generate_merchants(50)

    print("Generating dates...")
    dates_df = generate_dates()

    print("Generating transactions...")
    transactions_df = generate_transactions(
        accounts_df['account_id'].tolist(),
        merchants_df['merchant_id'].tolist(),
        dates_df['date_id'].tolist(),
        500
    )

    customers_df.to_csv(f'{output_dir}/customers.csv', index = False)
    accounts_df.to_csv(f'{output_dir}/accounts.csv', index=False)
    merchants_df.to_csv(f'{output_dir}/merchants.csv', index=False)
    dates_df.to_csv(f'{output_dir}/dates.csv', index=False)
    transactions_df.to_csv(f'{output_dir}/transactions.csv', index=False)

    print("All CSVs saved to", output_dir)

if __name__ == '__main__':
    main()



