"""Generate the three demo datasets used throughout the README examples.

Outputs (written to the current directory):
  1. customer_churn.csv     (7,043 rows) - Classification
  2. house_price.csv        (545 rows)   - Regression
  3. sales_timeseries.csv   (1,000 rows) - Time Series
"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Single global seed so the whole run is reproducible.
np.random.seed(42)

print("=" * 60)
print("Generating Test Datasets for MCP Data Analysis System")
print("=" * 60)


# ========================================
# Dataset 1: Customer Churn (Classification)
# ========================================
print("\n[1/3] Generating customer_churn.csv...")

n_customers = 7043

gender = np.random.choice(["Male", "Female"], n_customers, p=[0.5, 0.5])
senior_citizen = np.random.choice([0, 1], n_customers, p=[0.84, 0.16])
partner = np.random.choice(["Yes", "No"], n_customers, p=[0.48, 0.52])
dependents = np.random.choice(["Yes", "No"], n_customers, p=[0.30, 0.70])
tenure = np.random.randint(0, 73, n_customers)  # months with the company

phone_service = np.random.choice(["Yes", "No"], n_customers, p=[0.90, 0.10])
internet_service = np.random.choice(
    ["DSL", "Fiber optic", "No"], n_customers, p=[0.34, 0.44, 0.22]
)
contract_type = np.random.choice(
    ["Month-to-month", "One year", "Two year"], n_customers, p=[0.55, 0.21, 0.24]
)
payment_method = np.random.choice(
    ["Electronic check", "Mailed check", "Bank transfer", "Credit card"],
    n_customers,
    p=[0.34, 0.23, 0.22, 0.21],
)

# Monthly charge driven by internet tier, plus a commitment discount: longer
# contracts pay less per month (this makes the README ANOVA example, contract
# vs monthly_charges, come out significant).
base_charge = np.select(
    [internet_service == "Fiber optic", internet_service == "DSL"],
    [85.0, 55.0],
    default=20.0,
)
contract_adjust = np.select(
    [contract_type == "Month-to-month", contract_type == "Two year"],
    [8.0, -10.0],
    default=0.0,
)
monthly_charges = np.round(base_charge + contract_adjust + np.random.normal(0, 8, n_customers), 2)
monthly_charges = np.clip(monthly_charges, 18.0, 120.0)
total_charges = np.round(monthly_charges * np.maximum(tenure, 1), 2)

# Churn probability: short tenure, month-to-month contracts, electronic-check
# payment and high monthly charges all push churn up (a learnable signal).
logit = (
    -1.0
    + (contract_type == "Month-to-month") * 1.4
    + (tenure < 12) * 1.2
    - (tenure > 48) * 1.0
    + (payment_method == "Electronic check") * 0.6
    + (monthly_charges > 80) * 0.5
    + (senior_citizen == 1) * 0.3
)
churn_prob = 1 / (1 + np.exp(-logit))
churn = np.where(np.random.random(n_customers) < churn_prob, "Yes", "No")

churn_df = pd.DataFrame(
    {
        "gender": gender,
        "senior_citizen": senior_citizen,
        "partner": partner,
        "dependents": dependents,
        "tenure": tenure,
        "phone_service": phone_service,
        "internet_service": internet_service,
        "contract_type": contract_type,
        "payment_method": payment_method,
        "monthly_charges": monthly_charges,
        "total_charges": total_charges,
        "churn": churn,
    }
)
churn_df.to_csv("customer_churn.csv", index=False)

print("✅ customer_churn.csv created!")
print(f"   Rows: {len(churn_df)}")
print(f"   Columns: {len(churn_df.columns)}")
print(f"   Churn rate: {(churn == 'Yes').mean() * 100:.1f}%")


# ========================================
# Dataset 2: House Price (Regression)
# ========================================
print("\n[2/3] Generating house_price.csv...")

n_houses = 545

areas = np.random.randint(500, 5000, n_houses)
bedrooms = np.random.choice([1, 2, 3, 4, 5], n_houses, p=[0.05, 0.15, 0.35, 0.30, 0.15])
bathrooms = np.random.choice([1, 2, 3, 4], n_houses, p=[0.15, 0.45, 0.30, 0.10])
stories = np.random.choice([1, 2, 3], n_houses, p=[0.50, 0.40, 0.10])
parking = np.random.choice([0, 1, 2, 3], n_houses, p=[0.10, 0.40, 0.40, 0.10])

mainroad = np.random.choice(["yes", "no"], n_houses, p=[0.85, 0.15])
guestroom = np.random.choice(["yes", "no"], n_houses, p=[0.35, 0.65])
basement = np.random.choice(["yes", "no"], n_houses, p=[0.40, 0.60])
hotwaterheating = np.random.choice(["yes", "no"], n_houses, p=[0.20, 0.80])
airconditioning = np.random.choice(["yes", "no"], n_houses, p=[0.60, 0.40])
furnishingstatus = np.random.choice(
    ["furnished", "semi-furnished", "unfurnished"], n_houses, p=[0.25, 0.35, 0.40]
)

base_price = areas * 100
price = base_price.copy()
price += bedrooms * 50000
price += bathrooms * 30000
price += stories * 25000
price += parking * 15000
price += (mainroad == "yes") * 80000
price += (guestroom == "yes") * 40000
price += (basement == "yes") * 60000
price += (hotwaterheating == "yes") * 20000
price += (airconditioning == "yes") * 35000

furnishing_bonus = {"furnished": 100000, "semi-furnished": 50000, "unfurnished": 0}
price += np.array([furnishing_bonus[f] for f in furnishingstatus])

price = price + np.random.normal(0, 50000, n_houses)
price = np.maximum(price, 100000)
price = price.astype(int)

# Create outliers (abnormally high prices)
outlier_indices = np.random.choice(n_houses, 35, replace=False)
price[outlier_indices] = (price[outlier_indices] * np.random.uniform(2.0, 4.0, 35)).astype(int)

house_df = pd.DataFrame(
    {
        "area": areas,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "stories": stories,
        "parking": parking,
        "mainroad": mainroad,
        "guestroom": guestroom,
        "basement": basement,
        "hotwaterheating": hotwaterheating,
        "airconditioning": airconditioning,
        "furnishingstatus": furnishingstatus,
        "price": price,
    }
)
house_df.to_csv("house_price.csv", index=False)

print("✅ house_price.csv created!")
print(f"   Rows: {len(house_df)}")
print(f"   Columns: {len(house_df.columns)}")
print(f"   Price range: ${house_df['price'].min():,} - ${house_df['price'].max():,}")
print("   Outliers added: 35 (high-priced houses)")


# ========================================
# Dataset 3: Sales Time Series
# ========================================
print("\n[3/3] Generating sales_timeseries.csv...")

start_date = datetime(2022, 1, 1)
n_days = 1000
dates = [start_date + timedelta(days=i) for i in range(n_days)]

# Base trend (growing over time)
trend = np.linspace(1000, 2000, n_days)

# Seasonal component (yearly seasonality)
day_of_year = np.array([d.timetuple().tm_yday for d in dates])
seasonal = 300 * np.sin(2 * np.pi * day_of_year / 365)

# Weekly pattern (higher on weekends)
day_of_week = np.array([d.weekday() for d in dates])
weekly = np.where((day_of_week == 5) | (day_of_week == 6), 200, 0)

# Random noise
noise = np.random.normal(0, 100, n_days)

sales = trend + seasonal + weekly + noise
sales = np.maximum(sales, 100).round(0).astype(int)

# Promotion flag (random promotions boost sales)
promotion = np.random.choice([0, 1], n_days, p=[0.85, 0.15])
sales = np.where(promotion == 1, sales * 1.3, sales).astype(int)

# Holiday flag (major holidays)
holidays = []
for date in dates:
    is_holiday = (
        (date.month == 1 and date.day == 1)  # New Year
        or (date.month == 12 and date.day == 25)  # Christmas
        or (date.month == 11 and 22 <= date.day <= 28 and date.weekday() == 3)  # Thanksgiving
        or (date.month == 7 and date.day == 4)  # Independence Day
    )
    holidays.append(1 if is_holiday else 0)

holidays = np.array(holidays)
sales = np.where(holidays == 1, sales * 1.5, sales).astype(int)

product_ids = np.random.choice(
    ["PROD_A", "PROD_B", "PROD_C", "PROD_D"], n_days, p=[0.35, 0.30, 0.20, 0.15]
)

sales_df = pd.DataFrame(
    {
        "date": dates,
        "product_id": product_ids,
        "sales": sales,
        "promotion": promotion,
        "holiday": holidays,
        "day_of_week": [d.strftime("%A") for d in dates],
        "month": [d.month for d in dates],
    }
)
sales_df.to_csv("sales_timeseries.csv", index=False)

print("✅ sales_timeseries.csv created!")
print(f"   Rows: {len(sales_df)}")
print(f"   Columns: {len(sales_df.columns)}")
print(f"   Date range: {sales_df['date'].min()} to {sales_df['date'].max()}")
print(f"   Sales range: {sales_df['sales'].min():,} - {sales_df['sales'].max():,}")
print(f"   Promotions: {sales_df['promotion'].sum()} days")
print(f"   Holidays: {sales_df['holiday'].sum()} days")

print("\n" + "=" * 60)
print("All test datasets generated successfully!")
print("=" * 60)
print("\nGenerated files:")
print("  1. customer_churn.csv (7,043 rows) - Classification")
print("  2. house_price.csv (545 rows) - Regression")
print("  3. sales_timeseries.csv (1,000 rows) - Time Series")
