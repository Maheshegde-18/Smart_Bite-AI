"""
SmartBite AI - Database module
SQLite schema and helper functions for food_records table.
"""

import sqlite3
import os
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get('SMARTBITE_DB_PATH', os.path.join(BASE_DIR, 'smartbite.db'))


def get_conn():
    """Return a SQLite connection with row_factory=sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the food_records table if it doesn't exist."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            day_of_week INTEGER,
            month INTEGER,
            is_weekend INTEGER,
            meal_type INTEGER,
            weather INTEGER,
            is_event INTEGER,
            temperature REAL,
            num_staff INTEGER,
            num_customers_expected INTEGER,
            actual_meals REAL,
            actual_waste REAL,
            predicted_meals REAL DEFAULT NULL,
            predicted_waste REAL DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    conn.commit()
    conn.close()


def insert_record(data_dict):
    """Insert a single record. Returns the lastrowid."""
    conn = get_conn()
    cursor = conn.cursor()
    cols = [
        'date', 'day_of_week', 'month', 'is_weekend', 'meal_type',
        'weather', 'is_event', 'temperature', 'num_staff',
        'num_customers_expected', 'actual_meals', 'actual_waste',
        'predicted_meals', 'predicted_waste'
    ]
    # Only use keys present in the dict
    keys = [c for c in cols if c in data_dict]
    placeholders = ', '.join(['?' for _ in keys])
    col_names = ', '.join(keys)
    values = [data_dict[k] for k in keys]
    cursor.execute(
        f'INSERT INTO food_records ({col_names}) VALUES ({placeholders})',
        values
    )
    conn.commit()
    rowid = cursor.lastrowid
    conn.close()
    return rowid


def bulk_insert(records_list):
    """
    Bulk-insert a list of dicts into food_records.
    Uses executemany for efficiency.
    """
    if not records_list:
        return
    conn = get_conn()
    cursor = conn.cursor()
    cols = [
        'date', 'day_of_week', 'month', 'is_weekend', 'meal_type',
        'weather', 'is_event', 'temperature', 'num_staff',
        'num_customers_expected', 'actual_meals', 'actual_waste',
        'predicted_meals', 'predicted_waste'
    ]
    # Determine which columns are present in the first record
    keys = [c for c in cols if c in records_list[0]]
    placeholders = ', '.join(['?' for _ in keys])
    col_names = ', '.join(keys)
    sql = f'INSERT INTO food_records ({col_names}) VALUES ({placeholders})'
    rows = [[r.get(k) for k in keys] for r in records_list]
    cursor.executemany(sql, rows)
    conn.commit()
    conn.close()


def get_all_records(limit=500):
    """Return list of dicts ordered by date DESC, up to limit rows."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM food_records ORDER BY date DESC LIMIT ?', (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_records_df():
    """Return a pandas DataFrame of all food_records."""
    conn = get_conn()
    df = pd.read_sql_query('SELECT * FROM food_records ORDER BY date ASC', conn)
    conn.close()
    return df


def get_dashboard_stats():
    """
    Return dashboard statistics dict:
      total_records, avg_meals, avg_waste_kg, waste_reduction_pct,
      recent_7days, waste_by_meal_type, meals_by_day_of_week
    """
    conn = get_conn()
    cursor = conn.cursor()

    # Basic aggregates
    cursor.execute('''
        SELECT
            COUNT(*) as total_records,
            AVG(actual_meals) as avg_meals,
            AVG(actual_waste) as avg_waste_kg,
            AVG(predicted_waste) as avg_predicted_waste
        FROM food_records
    ''')
    row = cursor.fetchone()
    total_records = row['total_records'] or 0
    avg_meals = round(row['avg_meals'] or 0, 2)
    avg_waste_kg = round(row['avg_waste_kg'] or 0, 2)
    avg_predicted_waste = row['avg_predicted_waste']

    # Waste reduction percentage
    if avg_predicted_waste is not None and avg_waste_kg > 0:
        waste_reduction_pct = round(
            ((avg_waste_kg - avg_predicted_waste) / avg_waste_kg) * 100, 2
        )
    else:
        waste_reduction_pct = 0.0

    # Recent 7 unique dates
    cursor.execute('''
        SELECT DISTINCT date FROM food_records ORDER BY date DESC LIMIT 7
    ''')
    recent_dates = [r['date'] for r in cursor.fetchall()]

    recent_7days = []
    for d in sorted(recent_dates):  # chronological order
        cursor.execute('''
            SELECT
                date,
                AVG(actual_meals) as actual_meals,
                AVG(predicted_meals) as predicted_meals,
                AVG(actual_waste) as actual_waste,
                AVG(predicted_waste) as predicted_waste
            FROM food_records
            WHERE date = ?
            GROUP BY date
        ''', (d,))
        r = cursor.fetchone()
        if r:
            recent_7days.append({
                'date': r['date'],
                'actual_meals': round(r['actual_meals'] or 0, 2),
                'predicted_meals': round(r['predicted_meals'] or 0, 2),
                'actual_waste': round(r['actual_waste'] or 0, 2),
                'predicted_waste': round(r['predicted_waste'] or 0, 2),
            })

    # Waste by meal type (0=breakfast, 1=lunch, 2=dinner)
    cursor.execute('''
        SELECT meal_type, AVG(actual_waste) as avg_waste
        FROM food_records
        GROUP BY meal_type
    ''')
    meal_type_map = {0: 'breakfast', 1: 'lunch', 2: 'dinner'}
    waste_by_meal_type = {'breakfast': 0, 'lunch': 0, 'dinner': 0}
    for r in cursor.fetchall():
        label = meal_type_map.get(r['meal_type'], str(r['meal_type']))
        waste_by_meal_type[label] = round(r['avg_waste'] or 0, 2)

    # Meals by day of week (0=Mon...6=Sun)
    cursor.execute('''
        SELECT day_of_week, AVG(actual_meals) as avg_meals
        FROM food_records
        GROUP BY day_of_week
        ORDER BY day_of_week
    ''')
    day_map = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}
    meals_by_day_of_week = {v: 0 for v in day_map.values()}
    for r in cursor.fetchall():
        label = day_map.get(r['day_of_week'], str(r['day_of_week']))
        meals_by_day_of_week[label] = round(r['avg_meals'] or 0, 2)

    conn.close()

    return {
        'total_records': total_records,
        'avg_meals': avg_meals,
        'avg_waste_kg': avg_waste_kg,
        'waste_reduction_pct': waste_reduction_pct,
        'recent_7days': recent_7days,
        'waste_by_meal_type': waste_by_meal_type,
        'meals_by_day_of_week': meals_by_day_of_week,
    }
