"""
LightGBM-based prediction model for token performance
Multi-task model predicting returns and pump probabilities
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
import json
import pickle
from loguru import logger
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
    precision_score,
    recall_score,
    accuracy_score
)


class TokenPredictor:
    """LightGBM model for predicting token performance"""

    def __init__(
        self,
        target_variable: str = "return_24h",
        task_type: str = "regression",
        model_params: Optional[Dict] = None
    ):
        """
        Initialize predictor

        Args:
            target_variable: Name of target variable to predict
            task_type: "regression" or "classification"
            model_params: LightGBM hyperparameters
        """
        self.target_variable = target_variable
        self.task_type = task_type
        self.model = None
        self.feature_names = None
        self.feature_importance = None

        # Default LightGBM parameters
        if model_params is None:
            if task_type == "regression":
                model_params = {
                    'objective': 'regression',
                    'metric': 'rmse',
                    'boosting_type': 'gbdt',
                    'num_leaves': 31,
                    'learning_rate': 0.05,
                    'feature_fraction': 0.8,
                    'bagging_fraction': 0.8,
                    'bagging_freq': 5,
                    'verbose': -1,
                    'n_estimators': 500,
                    'random_state': 42
                }
            else:  # classification
                model_params = {
                    'objective': 'binary',
                    'metric': 'auc',
                    'boosting_type': 'gbdt',
                    'num_leaves': 31,
                    'learning_rate': 0.05,
                    'feature_fraction': 0.8,
                    'bagging_fraction': 0.8,
                    'bagging_freq': 5,
                    'verbose': -1,
                    'n_estimators': 500,
                    'random_state': 42
                }

        self.model_params = model_params
        logger.info(f"Initialized {task_type} predictor for {target_variable}")

    def prepare_data(
        self,
        features_df: pd.DataFrame,
        labels_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare data for training

        Args:
            features_df: DataFrame of features
            labels_df: DataFrame of labels

        Returns:
            Tuple of (X, y)
        """
        # Merge features and labels
        data = features_df.merge(
            labels_df[['token_address', 'migration_time', self.target_variable]],
            on=['token_address', 'migration_time'],
            how='inner'
        )

        # Remove non-feature columns
        exclude_cols = ['token_address', 'migration_time']
        feature_cols = [col for col in data.columns if col not in exclude_cols + [self.target_variable]]

        X = data[feature_cols]
        y = data[self.target_variable]

        # Handle missing values
        X = X.fillna(0)

        # Store feature names
        self.feature_names = feature_cols

        logger.info(f"Prepared data: {len(X)} samples, {len(feature_cols)} features")
        return X, y

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        early_stopping_rounds: int = 50
    ) -> Dict[str, Any]:
        """
        Train the model

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            early_stopping_rounds: Early stopping rounds

        Returns:
            Training metrics dict
        """
        logger.info(f"Training model with {len(X_train)} samples...")

        # Create LightGBM model
        if self.task_type == "regression":
            self.model = lgb.LGBMRegressor(**self.model_params)
        else:
            self.model = lgb.LGBMClassifier(**self.model_params)

        # Prepare validation set
        eval_set = None
        callbacks = []

        if X_val is not None and y_val is not None:
            eval_set = [(X_val, y_val)]
            callbacks = [
                lgb.early_stopping(stopping_rounds=early_stopping_rounds, verbose=False),
                lgb.log_evaluation(period=100)
            ]

        # Train
        self.model.fit(
            X_train,
            y_train,
            eval_set=eval_set,
            callbacks=callbacks
        )

        # Compute feature importance
        self.feature_importance = pd.DataFrame({
            'feature': X_train.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        logger.info("Training complete")
        logger.info(f"Top 5 features: {self.feature_importance.head()['feature'].tolist()}")

        # Compute training metrics
        y_pred_train = self.model.predict(X_train)
        metrics = self.evaluate(y_train, y_pred_train, "train")

        if X_val is not None:
            y_pred_val = self.model.predict(X_val)
            val_metrics = self.evaluate(y_val, y_pred_val, "val")
            metrics.update(val_metrics)

        return metrics

    def evaluate(
        self,
        y_true: pd.Series,
        y_pred: np.ndarray,
        prefix: str = ""
    ) -> Dict[str, float]:
        """
        Evaluate model performance

        Args:
            y_true: True labels
            y_pred: Predicted labels
            prefix: Metric name prefix (e.g., "train", "val")

        Returns:
            Dict of metrics
        """
        metrics = {}

        if self.task_type == "regression":
            metrics[f'{prefix}_mae'] = mean_absolute_error(y_true, y_pred)
            metrics[f'{prefix}_rmse'] = np.sqrt(mean_squared_error(y_true, y_pred))
            metrics[f'{prefix}_r2'] = r2_score(y_true, y_pred)
        else:
            # Binary classification
            y_pred_binary = (y_pred > 0.5).astype(int)
            metrics[f'{prefix}_accuracy'] = accuracy_score(y_true, y_pred_binary)
            metrics[f'{prefix}_precision'] = precision_score(y_true, y_pred_binary, zero_division=0)
            metrics[f'{prefix}_recall'] = recall_score(y_true, y_pred_binary, zero_division=0)

            # AUC if probabilities available
            try:
                y_proba = self.model.predict_proba(y_pred)[:, 1] if hasattr(self.model, 'predict_proba') else y_pred
                metrics[f'{prefix}_auc'] = roc_auc_score(y_true, y_proba)
            except:
                pass

        return metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions

        Args:
            X: Feature DataFrame

        Returns:
            Predictions array
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        # Ensure features match training
        if self.feature_names:
            missing_cols = set(self.feature_names) - set(X.columns)
            if missing_cols:
                logger.warning(f"Missing features: {missing_cols}, filling with 0")
                for col in missing_cols:
                    X[col] = 0

            X = X[self.feature_names]

        return self.model.predict(X)

    def predict_with_explanation(
        self,
        X: pd.DataFrame,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Make predictions with feature importance explanation

        Args:
            X: Feature DataFrame
            top_n: Number of top features to explain

        Returns:
            List of prediction dicts with explanations
        """
        predictions = self.predict(X)
        results = []

        for idx, pred in enumerate(predictions):
            # Get feature values for this sample
            sample_features = X.iloc[idx]

            # Get top contributing features
            feature_contributions = []
            for _, row in self.feature_importance.head(top_n).iterrows():
                feature_name = row['feature']
                feature_value = sample_features[feature_name]
                feature_contrib = row['importance']

                feature_contributions.append({
                    'feature': feature_name,
                    'value': feature_value,
                    'importance': feature_contrib
                })

            results.append({
                'prediction': float(pred),
                'top_features': feature_contributions
            })

        return results

    def save(self, model_path: str):
        """
        Save model to disk

        Args:
            model_path: Path to save model
        """
        model_dir = Path(model_path).parent
        model_dir.mkdir(parents=True, exist_ok=True)

        # Save model
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'target_variable': self.target_variable,
                'task_type': self.task_type,
                'feature_names': self.feature_names,
                'feature_importance': self.feature_importance,
                'model_params': self.model_params
            }, f)

        logger.info(f"Model saved to {model_path}")

    def load(self, model_path: str):
        """
        Load model from disk

        Args:
            model_path: Path to model file
        """
        with open(model_path, 'rb') as f:
            data = pickle.load(f)

        self.model = data['model']
        self.target_variable = data['target_variable']
        self.task_type = data['task_type']
        self.feature_names = data['feature_names']
        self.feature_importance = data['feature_importance']
        self.model_params = data['model_params']

        logger.info(f"Model loaded from {model_path}")


def train_model_pipeline(
    features_csv: str,
    labels_csv: str,
    target_variable: str = "return_24h",
    task_type: str = "regression",
    test_size: float = 0.2,
    model_save_path: str = "./models/token_predictor.pkl"
) -> TokenPredictor:
    """
    Complete training pipeline

    Args:
        features_csv: Path to features CSV
        labels_csv: Path to labels CSV
        target_variable: Target variable name
        task_type: "regression" or "classification"
        test_size: Test set fraction
        model_save_path: Where to save trained model

    Returns:
        Trained predictor
    """
    logger.info("Starting training pipeline...")

    # Load data
    features_df = pd.read_csv(features_csv)
    labels_df = pd.read_csv(labels_csv)

    # Initialize predictor
    predictor = TokenPredictor(target_variable=target_variable, task_type=task_type)

    # Prepare data
    X, y = predictor.prepare_data(features_df, labels_df)

    # Train/test split (time-based would be better for production)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42
    )

    # Further split train into train/val
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.15, random_state=42
    )

    # Train
    metrics = predictor.train(X_train, y_train, X_val, y_val)
    logger.info(f"Training metrics: {metrics}")

    # Evaluate on test set
    y_pred_test = predictor.predict(X_test)
    test_metrics = predictor.evaluate(y_test, y_pred_test, "test")
    logger.info(f"Test metrics: {test_metrics}")

    # Save model
    predictor.save(model_save_path)

    return predictor


# Example usage
def main():
    # Create mock data for testing
    np.random.seed(42)

    n_samples = 1000
    n_features = 20

    mock_features = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )
    mock_features['token_address'] = [f'TOKEN{i}' for i in range(n_samples)]
    mock_features['migration_time'] = pd.date_range('2024-01-01', periods=n_samples, freq='6H')

    mock_labels = pd.DataFrame({
        'token_address': mock_features['token_address'],
        'migration_time': mock_features['migration_time'],
        'return_24h': np.random.randn(n_samples) * 0.2 + 0.05  # Mean 5% return
    })

    # Save to CSV
    mock_features.to_csv('data/mock_features.csv', index=False)
    mock_labels.to_csv('data/mock_labels.csv', index=False)

    # Train model
    predictor = train_model_pipeline(
        'data/mock_features.csv',
        'data/mock_labels.csv',
        target_variable='return_24h',
        task_type='regression'
    )

    print("Training complete!")


if __name__ == "__main__":
    main()
