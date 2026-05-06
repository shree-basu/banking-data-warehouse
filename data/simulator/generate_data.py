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
            'age': random.randomint(21,65),
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
            'balance': round(random.uniform(1000,500000),2)
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