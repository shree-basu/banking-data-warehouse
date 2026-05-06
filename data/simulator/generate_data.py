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