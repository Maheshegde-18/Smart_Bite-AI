# SYNTHETIC DATASET - Generated with seed=42 for reproducibility
"""
SmartBite AI - Synthetic Dataset Generator
Generates 2000 rows of realistic food demand / waste data and saves to CSV.
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Allow running standalone or as part of the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'smartbite_dataset.csv')


def generate_dataset(n=2000, seed=42):
    """
    Generate realistic synthetic food demand/waste data.

    Columns:
      date                   - YYYY-MM-DD string
      day_of_week            - int 0 (Mon) to 6 (Sun)
      month                  - int 1-12
      is_weekend             - int 0/1
      meal_type              - int 0=breakfast, 1=lunch, 2=dinner
      weather                - int 0=sunny, 1=cloudy, 2=rainy
      is_event               - int 0/1
      temperature            - float 10-40 (°C)
      num_staff              - int 5-30
      num_customers_expected - int 50-500
      actual_meals           - float (target 1: meals consumed)
      actual_waste           - float kg (target 2: food waste)
    """
    rng = np.random.default_rng(seed)

    start_date = datetime(2022, 1, 1)
    dates = [start_date + timedelta(days=int(d)) for d in
             np.sort(rng.choice(730, size=n, replace=True))]
    date_strs = [d.strftime('%Y-%m-%d') for d in dates]
    day_of_week = [d.weekday() for d in dates]
    month = [d.month for d in dates]
    is_weekend = [1 if d.weekday() >= 5 else 0 for d in dates]

    meal_type = rng.integers(0, 3, size=n)
    weather = rng.integers(0, 3, size=n)
    is_event = rng.choice([0, 1], size=n, p=[0.85, 0.15])

    temperature = rng.uniform(10, 40, size=n).round(1)
    num_staff = rng.integers(5, 31, size=n)
    num_customers_expected = rng.integers(50, 501, size=n)

    # actual_meals
    meal_type_lunch_bonus = (meal_type == 1).astype(int)
    num_staff_ratio_effect = num_staff / num_staff.mean()
    noise_meals = rng.normal(0, 15, size=n)
    actual_meals = (
        0.80 * num_customers_expected
        + 20 * is_event
        + 15 * np.array(is_weekend)
        - 8 * (weather == 2).astype(int)
        + 5 * meal_type_lunch_bonus
        - 3 * num_staff_ratio_effect
        + noise_meals
    )
    actual_meals = np.clip(actual_meals, 10, None).round(2)

    # actual_waste
    noise_waste = rng.normal(0, 2, size=n)
    actual_waste = (
        0.10 * actual_meals
        - 5 * is_event
        + 4 * (weather == 2).astype(int)
        + 2 * (meal_type == 2).astype(int)
        + noise_waste
    )
    actual_waste = np.clip(actual_waste, 0.5, None).round(2)

    df = pd.DataFrame({
        'date': date_strs,
        'day_of_week': day_of_week,
        'month': month,
        'is_weekend': is_weekend,
        'meal_type': meal_type.tolist(),
        'weather': weather.tolist(),
        'is_event': is_event.tolist(),
        'temperature': temperature.tolist(),
        'num_staff': num_staff.tolist(),
        'num_customers_expected': num_customers_expected.tolist(),
        'actual_meals': actual_meals.tolist(),
        'actual_waste': actual_waste.tolist(),
    })
    return df


if __name__ == '__main__':
    df = generate_dataset(n=2000, seed=42)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Dataset generated: {len(df)} rows")
    print("\nColumn descriptions:")
    print("  date                   - Date of record (YYYY-MM-DD)")
    print("  day_of_week            - 0=Monday ... 6=Sunday")
    print("  month                  - 1-12")
    print("  is_weekend             - 1 if Saturday or Sunday, else 0")
    print("  meal_type              - 0=Breakfast, 1=Lunch, 2=Dinner")
    print("  weather                - 0=Sunny, 1=Cloudy, 2=Rainy")
    print("  is_event               - 1 if special event day, else 0")
    print("  temperature            - Ambient temperature (°C), range 10-40")
    print("  num_staff              - Number of staff on duty, range 5-30")
    print("  num_customers_expected - Expected customers, range 50-500")
    print("  actual_meals           - Meals actually consumed (target 1)")
    print("  actual_waste           - Food waste in kg (target 2)")
    print(f"\nSaved to: {OUTPUT_PATH}")
    print("\nSample rows:")
    print(df.head(5).to_string(index=False))
