"""
SmartBite AI - Main Flask Application
Predicts food demand and waste using Multiple Linear Regression.
"""

import os
import json
import pickle
import logging
import sqlite3
from datetime import datetime

import numpy as np
import pandas as pd
from flask import (
    Flask, render_template, request, redirect, url_for,
    jsonify
)

# Optional .env loading
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Path setup so models package is importable regardless of CWD
# ---------------------------------------------------------------------------
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from models.database import (
    init_db, insert_record, bulk_insert,
    get_all_records, get_records_df, get_dashboard_stats
)
from models.ml_models import SmartBiteModels

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'smartbite-dev-secret-key-2024')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(BASE_DIR, 'models')
SAVED_MODELS_PATH = os.path.join(MODELS_DIR, 'saved_models.pkl')
# Legacy single-model pkl paths (kept for backward compat check)
MEAL_MODEL_PKL = os.path.join(MODELS_DIR, 'meal_model.pkl')
WASTE_MODEL_PKL = os.path.join(MODELS_DIR, 'waste_model.pkl')

sb_models = SmartBiteModels()


def startup_init():
    """Called once at startup: init DB, train models if needed, populate DB if empty."""
    init_db()
    logger.info("Database initialised.")

    if not os.path.exists(SAVED_MODELS_PATH):
        logger.info("No trained models found — generating dataset and training…")
        df = sb_models.generate_dataset()
        metrics = sb_models.train(df)
        logger.info(f"Models trained. Metrics: {metrics}")
    else:
        logger.info("Trained models found — skipping training.")

    # Check if DB is empty; if so, populate with synthetic dataset and predictions
    stats = get_dashboard_stats()
    if stats.get('total_records', 0) == 0:
        logger.info("DB is empty — generating dataset and populating DB…")
        df = sb_models.generate_dataset()
        records = df.to_dict(orient='records')
        for rec in records:
            try:
                preds = sb_models.predict(rec)
                rec['predicted_meals'] = preds['meals']
                rec['predicted_waste'] = preds['waste']
            except Exception:
                rec['predicted_meals'] = None
                rec['predicted_waste'] = None
        bulk_insert(records)
        logger.info(f"Populated DB with {len(records)} synthetic records.")


# Run startup
with app.app_context():
    startup_init()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/data-entry', methods=['GET', 'POST'])
def data_entry():
    if request.method == 'GET':
        return render_template('data_entry.html')

    # POST — validate & save
    try:
        data = request.get_json(force=True) if request.is_json else request.form.to_dict()

        required = [
            'date', 'day_of_week', 'month', 'is_weekend', 'meal_type',
            'weather', 'is_event', 'temperature', 'num_staff',
            'num_customers_expected', 'actual_meals', 'actual_waste'
        ]
        missing = [f for f in required if f not in data or data[f] == '']
        if missing:
            return jsonify({'success': False, 'message': f'Missing fields: {missing}'}), 400

        record = {
            'date': str(data['date']),
            'day_of_week': int(data['day_of_week']),
            'month': int(data['month']),
            'is_weekend': int(data['is_weekend']),
            'meal_type': int(data['meal_type']),
            'weather': int(data['weather']),
            'is_event': int(data['is_event']),
            'temperature': float(data['temperature']),
            'num_staff': int(data['num_staff']),
            'num_customers_expected': int(data['num_customers_expected']),
            'actual_meals': float(data['actual_meals']),
            'actual_waste': float(data['actual_waste']),
        }

        # Run predictions
        try:
            preds = sb_models.predict(record)
            record['predicted_meals'] = preds['meals']
            record['predicted_waste'] = preds['waste']
        except Exception as e:
            logger.warning(f"Prediction failed during data-entry: {e}")
            record['predicted_meals'] = None
            record['predicted_waste'] = None

        rowid = insert_record(record)
        return jsonify({'success': True, 'message': f'Record saved with ID {rowid}.'}), 201

    except Exception as e:
        logger.exception("Error in /data-entry POST")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/upload-csv', methods=['GET', 'POST'])
def upload_csv():
    if request.method == 'GET':
        return render_template('upload_csv.html')

    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded.'}), 400

        f = request.files['file']
        if not f.filename.endswith('.csv'):
            return jsonify({'success': False, 'message': 'Only CSV files are accepted.'}), 400

        df = pd.read_csv(f)

        required_cols = [
            'date', 'day_of_week', 'month', 'is_weekend', 'meal_type',
            'weather', 'is_event', 'temperature', 'num_staff',
            'num_customers_expected', 'actual_meals', 'actual_waste'
        ]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            return jsonify({
                'success': False,
                'message': f'CSV missing columns: {missing_cols}'
            }), 400

        records = df[required_cols].to_dict(orient='records')

        # Add predictions
        for rec in records:
            try:
                preds = sb_models.predict(rec)
                rec['predicted_meals'] = preds['meals']
                rec['predicted_waste'] = preds['waste']
            except Exception:
                rec['predicted_meals'] = None
                rec['predicted_waste'] = None

        bulk_insert(records)
        return jsonify({
            'success': True,
            'message': f'Uploaded and inserted {len(records)} records.'
        }), 201

    except Exception as e:
        logger.exception("Error in /upload-csv POST")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if request.method == 'GET':
        return render_template('predict.html')

    try:
        data = request.get_json(force=True)
        required = [
            'day_of_week', 'month', 'is_weekend', 'meal_type',
            'weather', 'is_event', 'temperature', 'num_staff',
            'num_customers_expected'
        ]
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({'success': False, 'message': f'Missing: {missing}'}), 400

        input_dict = {k: data[k] for k in required}
        # Coerce types
        input_dict['day_of_week'] = int(input_dict['day_of_week'])
        input_dict['month'] = int(input_dict['month'])
        input_dict['is_weekend'] = int(input_dict['is_weekend'])
        input_dict['meal_type'] = int(input_dict['meal_type'])
        input_dict['weather'] = int(input_dict['weather'])
        input_dict['is_event'] = int(input_dict['is_event'])
        input_dict['temperature'] = float(input_dict['temperature'])
        input_dict['num_staff'] = int(input_dict['num_staff'])
        input_dict['num_customers_expected'] = int(input_dict['num_customers_expected'])

        preds = sb_models.predict(input_dict)
        metrics = sb_models.get_metrics()

        return jsonify({
            'meals_pred': preds['meals'],
            'waste_pred': preds['waste'],
            'confidence_metrics': {
                'meal_r2': metrics['meal_metrics'].get('r2'),
                'waste_r2': metrics['waste_metrics'].get('r2'),
                'meal_mae': metrics['meal_metrics'].get('mae'),
                'waste_mae': metrics['waste_metrics'].get('mae'),
            }
        })

    except Exception as e:
        logger.exception("Error in /predict POST")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/history')
def history():
    return render_template('history.html')


@app.route('/api/history')
def api_history():
    try:
        records = get_all_records(limit=500)
        # Keep only the specified keys
        keys = [
            'id', 'date', 'day_of_week', 'meal_type', 'weather',
            'is_event', 'temperature', 'num_staff', 'num_customers_expected',
            'actual_meals', 'actual_waste', 'predicted_meals', 'predicted_waste'
        ]
        filtered = [{k: r.get(k) for k in keys} for r in records]
        return jsonify(filtered)
    except Exception as e:
        logger.exception("Error in /api/history")
        return jsonify({'error': str(e)}), 500


@app.route('/performance')
def performance():
    return render_template('performance.html')


@app.route('/api/performance')
def api_performance():
    try:
        metrics = sb_models.get_metrics()
        importance = sb_models.get_feature_importance()
        return jsonify({
            'meal_metrics': metrics['meal_metrics'],
            'waste_metrics': metrics['waste_metrics'],
            'feature_importance': importance,
            'actual_vs_predicted_meals': metrics['actual_vs_predicted_meals'],
            'actual_vs_predicted_waste': metrics['actual_vs_predicted_waste'],
        })
    except Exception as e:
        logger.exception("Error in /api/performance")
        return jsonify({'error': str(e)}), 500


@app.route('/recommendations')
def recommendations():
    return render_template('recommendations.html')


@app.route('/api/recommendations')
def api_recommendations():
    try:
        stats = get_dashboard_stats()
        recs = []

        avg_waste = stats.get('avg_waste_kg', 0)
        avg_meals = stats.get('avg_meals', 0)
        waste_reduction_pct = stats.get('waste_reduction_pct', 0)

        # Recommendation 1: waste level
        if avg_waste > 20:
            recs.append({
                'category': 'Waste Reduction',
                'priority': 'High',
                'title': 'High Average Food Waste Detected',
                'description': (
                    f'Your average food waste is {avg_waste:.1f} kg per session. '
                    'Consider reducing batch sizes and improving demand forecasting.'
                ),
                'action': 'Review portion sizes and implement just-in-time cooking.'
            })
        elif avg_waste > 10:
            recs.append({
                'category': 'Waste Reduction',
                'priority': 'Medium',
                'title': 'Moderate Food Waste',
                'description': (
                    f'Average waste of {avg_waste:.1f} kg per session can be improved.'
                ),
                'action': 'Use predicted waste figures to adjust preparation quantities.'
            })
        else:
            recs.append({
                'category': 'Waste Reduction',
                'priority': 'Low',
                'title': 'Waste Levels Under Control',
                'description': f'Average waste of {avg_waste:.1f} kg per session is acceptable.',
                'action': 'Maintain current practices and monitor trends.'
            })

        # Recommendation 2: waste by meal type
        wbmt = stats.get('waste_by_meal_type', {})
        if wbmt:
            worst_meal = max(wbmt, key=lambda k: wbmt[k])
            recs.append({
                'category': 'Meal Planning',
                'priority': 'Medium',
                'title': f'High Waste During {worst_meal.capitalize()}',
                'description': (
                    f'{worst_meal.capitalize()} meals generate the most waste '
                    f'({wbmt[worst_meal]:.1f} kg avg).'
                ),
                'action': (
                    f'Adjust {worst_meal} preparation quantities using the prediction tool '
                    'before each service.'
                )
            })

        # Recommendation 3: meals_by_day_of_week — lowest demand day
        mbdow = stats.get('meals_by_day_of_week', {})
        if mbdow:
            quiet_day = min(mbdow, key=lambda k: mbdow[k])
            recs.append({
                'category': 'Staffing',
                'priority': 'Low',
                'title': f'Reduce Staffing on {quiet_day}',
                'description': (
                    f'{quiet_day} has the lowest average meals served '
                    f'({mbdow[quiet_day]:.0f} meals).'
                ),
                'action': 'Consider reducing staff count or shifting duties on this day.'
            })

        # Recommendation 4: model accuracy
        try:
            m = sb_models.get_metrics()
            meal_r2 = m['meal_metrics'].get('r2', 0)
            if meal_r2 < 0.7:
                recs.append({
                    'category': 'Model Performance',
                    'priority': 'High',
                    'title': 'Model Accuracy Needs Improvement',
                    'description': (
                        f'Meal demand model R² = {meal_r2:.2f}. '
                        'More data or feature engineering may help.'
                    ),
                    'action': 'Collect more historical records and retrain via /api/retrain.'
                })
        except Exception:
            pass

        # Recommendation 5: waste_reduction_pct
        if waste_reduction_pct > 0:
            recs.append({
                'category': 'Success',
                'priority': 'Info',
                'title': 'AI Predictions Are Helping',
                'description': (
                    f'Predicted waste is {waste_reduction_pct:.1f}% lower than actual average, '
                    'indicating the model is capturing patterns.'
                ),
                'action': 'Keep entering daily records to continuously improve model accuracy.'
            })

        return jsonify({'recommendations': recs, 'stats_snapshot': {
            'total_records': stats.get('total_records'),
            'avg_meals': avg_meals,
            'avg_waste_kg': avg_waste,
            'waste_reduction_pct': waste_reduction_pct,
        }})

    except Exception as e:
        logger.exception("Error in /api/recommendations")
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    try:
        stats = get_dashboard_stats()
        return jsonify(stats)
    except Exception as e:
        logger.exception("Error in /api/dashboard-stats")
        return jsonify({'error': str(e)}), 500


@app.route('/api/retrain', methods=['POST'])
def api_retrain():
    try:
        df = get_records_df()
        if df.empty or len(df) < 10:
            return jsonify({
                'success': False,
                'message': 'Not enough data to retrain (need at least 10 records).'
            }), 400

        required_cols = [
            'day_of_week', 'month', 'is_weekend', 'meal_type',
            'weather', 'is_event', 'temperature', 'num_staff',
            'num_customers_expected', 'actual_meals', 'actual_waste', 'date'
        ]
        for col in required_cols:
            if col not in df.columns:
                return jsonify({
                    'success': False,
                    'message': f'Missing column in DB data: {col}'
                }), 400

        metrics = sb_models.train(df)
        logger.info(f"Retrain complete. Metrics: {metrics}")
        return jsonify({'success': True, 'metrics': metrics})

    except Exception as e:
        logger.exception("Error in /api/retrain")
        return jsonify({'success': False, 'message': str(e)}), 500


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1').lower() in ('true', '1')
    app.run(debug=debug, host='0.0.0.0', port=port)
