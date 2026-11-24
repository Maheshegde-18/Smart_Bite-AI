"""
SmartBite AI - Machine Learning Models
Handles dataset generation, model training, prediction, and metrics.
"""

import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.environ.get('SMARTBITE_MODELS_DIR', os.path.join(BASE_DIR, 'models'))
SAVED_MODELS_PATH = os.path.join(MODELS_DIR, 'saved_models.pkl')

FEATURE_COLS = [
    'day_of_week', 'month', 'is_weekend', 'meal_type',
    'weather', 'is_event', 'temperature', 'num_staff',
    'num_customers_expected'
]


class SmartBiteModels:

    def generate_dataset(self, n=2000, seed=42):
        """
        Generate a realistic synthetic dataset with n rows.
        Returns a DataFrame with all required columns.
        """
        rng = np.random.default_rng(seed)

        # Generate dates spread over ~2 years
        start_date = datetime(2022, 1, 1)
        dates = [start_date + timedelta(days=int(d)) for d in
                 np.sort(rng.choice(730, size=n, replace=True))]
        date_strs = [d.strftime('%Y-%m-%d') for d in dates]
        day_of_week = [d.weekday() for d in dates]   # 0=Mon, 6=Sun
        month = [d.month for d in dates]
        is_weekend = [1 if d.weekday() >= 5 else 0 for d in dates]

        # Categorical features
        meal_type = rng.integers(0, 3, size=n)       # 0=breakfast,1=lunch,2=dinner
        weather = rng.integers(0, 3, size=n)         # 0=sunny,1=cloudy,2=rainy
        is_event = rng.choice([0, 1], size=n, p=[0.85, 0.15])

        # Continuous features
        temperature = rng.uniform(10, 40, size=n).round(1)
        num_staff = rng.integers(5, 31, size=n)
        num_customers_expected = rng.integers(50, 501, size=n)

        # --- actual_meals ---
        meal_type_lunch_bonus = (meal_type == 1).astype(int)
        num_staff_ratio_effect = num_staff / num_staff.mean()  # centred ratio
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

        # --- actual_waste ---
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

    def train(self, df=None):
        """
        Train both LinearRegression models (meals & waste).
        If df is None, generate synthetic dataset.
        Saves all artifacts to saved_models.pkl.
        Returns metrics dict.
        """
        if df is None:
            df = self.generate_dataset()

        # Sort chronologically
        df = df.sort_values('date').reset_index(drop=True)

        split_idx = int(len(df) * 0.80)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]

        X_train = train_df[FEATURE_COLS].values
        X_test = test_df[FEATURE_COLS].values
        y_meals_train = train_df['actual_meals'].values
        y_meals_test = test_df['actual_meals'].values
        y_waste_train = train_df['actual_waste'].values
        y_waste_test = test_df['actual_waste'].values

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train models
        meal_model = LinearRegression()
        meal_model.fit(X_train_scaled, y_meals_train)

        waste_model = LinearRegression()
        waste_model.fit(X_train_scaled, y_waste_train)

        # Predictions on test set
        meals_pred = meal_model.predict(X_test_scaled)
        waste_pred = waste_model.predict(X_test_scaled)

        # Metrics
        meal_mae = float(mean_absolute_error(y_meals_test, meals_pred))
        meal_rmse = float(np.sqrt(mean_squared_error(y_meals_test, meals_pred)))
        meal_r2 = float(r2_score(y_meals_test, meals_pred))

        waste_mae = float(mean_absolute_error(y_waste_test, waste_pred))
        waste_rmse = float(np.sqrt(mean_squared_error(y_waste_test, waste_pred)))
        waste_r2 = float(r2_score(y_waste_test, waste_pred))

        metrics = {
            'meal_metrics': {
                'mae': round(meal_mae, 4),
                'rmse': round(meal_rmse, 4),
                'r2': round(meal_r2, 4),
            },
            'waste_metrics': {
                'mae': round(waste_mae, 4),
                'rmse': round(waste_rmse, 4),
                'r2': round(waste_r2, 4),
            },
        }

        # Sample 50 points for the actual-vs-predicted charts
        sample_size = min(50, len(test_df))
        sample_idx = np.linspace(0, len(test_df) - 1, sample_size, dtype=int)

        actual_vs_predicted_meals = [
            {'actual': float(y_meals_test[i]), 'predicted': float(meals_pred[i])}
            for i in sample_idx
        ]
        actual_vs_predicted_waste = [
            {'actual': float(y_waste_test[i]), 'predicted': float(waste_pred[i])}
            for i in sample_idx
        ]

        # Feature importance (linear coefficients)
        feature_importance = {
            'meal_importance': dict(zip(FEATURE_COLS, meal_model.coef_.tolist())),
            'waste_importance': dict(zip(FEATURE_COLS, waste_model.coef_.tolist())),
        }

        # Persist everything
        os.makedirs(MODELS_DIR, exist_ok=True)
        save_dict = {
            'meal_model': meal_model,
            'waste_model': waste_model,
            'scaler': scaler,
            'feature_cols': FEATURE_COLS,
            'metrics': metrics,
            'actual_vs_predicted_meals': actual_vs_predicted_meals,
            'actual_vs_predicted_waste': actual_vs_predicted_waste,
            'feature_importance': feature_importance,
        }
        with open(SAVED_MODELS_PATH, 'wb') as f:
            pickle.dump(save_dict, f)

        return metrics

    def _load(self):
        """Load saved_models.pkl and return the dict."""
        with open(SAVED_MODELS_PATH, 'rb') as f:
            return pickle.load(f)

    def predict(self, input_dict):
        """
        Run both models on a single input.
        input_dict must contain all FEATURE_COLS keys.
        Returns {'meals': float, 'waste': float}.
        """
        data = self._load()
        scaler = data['scaler']
        meal_model = data['meal_model']
        waste_model = data['waste_model']
        feature_cols = data['feature_cols']

        row = pd.DataFrame([{col: input_dict[col] for col in feature_cols}])
        row_scaled = scaler.transform(row.values)
        meals = float(meal_model.predict(row_scaled)[0])
        waste = float(waste_model.predict(row_scaled)[0])
        meals = max(0.0, round(meals, 2))
        waste = max(0.0, round(waste, 2))
        return {'meals': meals, 'waste': waste}

    def get_metrics(self):
        """
        Return metrics and actual_vs_predicted lists from saved models.
        """
        data = self._load()
        m = data['metrics']
        return {
            'meal_metrics': m.get('meal_metrics', {}),
            'waste_metrics': m.get('waste_metrics', {}),
            'actual_vs_predicted_meals': data.get('actual_vs_predicted_meals', []),
            'actual_vs_predicted_waste': data.get('actual_vs_predicted_waste', []),
        }

    def get_feature_importance(self):
        """
        Return feature importance (linear coefficients) from saved models.
        """
        data = self._load()
        return data.get('feature_importance', {})
