"""Prediction Service layer for ML model lifecycle, inference, and metadata management.

This service maintains the central model registry, loading the four trained
scikit-learn pipelines (D_7, D_15, D_30, D_90) and metadata once at application
startup. It handles single- and multi-horizon inference requests, formats features
matching the pipeline contract, guarantees non-negative finite predictions, and
handles unseen product SKUs via native infrequent categorical encoding.
"""

import json
import joblib
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from app.core.config import settings
from app.schemas.forecast import (
    ForecastRequest,
    ForecastResponse,
    HorizonPredictionDetail,
    SUPPORTED_HORIZONS
)


class PredictionService:
    """Manages the in-memory registry of trained forecasting pipelines."""

    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = Path(models_dir) if models_dir else Path(settings.MODELS_DIR)
        self.models: Dict[int, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.is_loaded: bool = False
        self.frequent_skus: set = set()
        self.supported_horizons: List[int] = list(SUPPORTED_HORIZONS)

    def load_models(self) -> None:
        """Loads all serialized model binaries and metadata into memory.
        
        Raises:
            FileNotFoundError: If required model binaries or metadata are missing.
            RuntimeError: If model loading fails or artifacts are corrupted.
        """
        print(f"[NEXORA PredictionService] Initializing ML model registry from: {self.models_dir}...")
        
        if not self.models_dir.is_dir():
            raise FileNotFoundError(
                f"Model directory does not exist: {self.models_dir}. "
                "Ensure models are trained and saved in backend/ml/models/."
            )

        metadata_path = self.models_dir / "models_metadata.json"
        if not metadata_path.is_file():
            raise FileNotFoundError(
                f"Model metadata manifest missing: {metadata_path}. "
                "Run 'python backend/ml/src/train.py' to generate model artifacts and metadata."
            )

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to parse model metadata from {metadata_path}: {e}")

        # Load and validate each horizon model
        loaded_models = {}
        for h in self.supported_horizons:
            model_filename = f"demand_model_{h}d.joblib"
            model_path = self.models_dir / model_filename
            
            if not model_path.is_file():
                raise FileNotFoundError(
                    f"Required model artifact missing for horizon D_{h}: {model_path}. "
                    "Ensure all 4 horizon models are trained and saved."
                )

            try:
                pipeline = joblib.load(model_path)
            except Exception as e:
                raise RuntimeError(f"Corrupted or invalid model artifact at {model_path}: {e}")

            if not hasattr(pipeline, "predict"):
                raise RuntimeError(f"Loaded object for horizon D_{h} does not have a predict method.")

            loaded_models[h] = pipeline

        self.models = loaded_models
        self.is_loaded = True

        # Extract frequent SKUs recognized by OneHotEncoder for informational warnings
        try:
            sample_model = self.models[7]
            preprocessor = sample_model.named_steps.get("preprocessor")
            if preprocessor:
                cat_encoder = preprocessor.named_transformers_.get("cat")
                if cat_encoder and hasattr(cat_encoder, "categories_"):
                    self.frequent_skus = set(cat_encoder.categories_[0])
        except Exception:
            self.frequent_skus = set()

        print(
            f"[NEXORA PredictionService] Successfully loaded {len(self.models)} forecasting models "
            f"([D_7, D_15, D_30, D_90]) into memory."
        )

    def ensure_loaded(self) -> None:
        """Ensures models are loaded; triggers loading if not already in memory."""
        if not self.is_loaded:
            self.load_models()

    def get_forecast(self, request: ForecastRequest) -> ForecastResponse:
        """Executes multi-horizon demand inference for a validated forecast request.
        
        Args:
            request: Validated ForecastRequest schema.
            
        Returns:
            ForecastResponse: Multi-horizon prediction response with metadata.
            
        Raises:
            RuntimeError: If models are not loaded and cannot be found.
        """
        self.ensure_loaded()

        sku = request.stock_code
        features = request.features
        requested_horizons = request.horizons or self.supported_horizons

        # Construct input DataFrame matching exact feature contract:
        # ['StockCode', 'DayOfWeek', 'Month', 'DayOfMonth', 'Lag1', 'Lag7', 'Lag14', 'Lag28', 'RollingMean7', 'RollingMean28']
        input_data = {
            "StockCode": [sku],
            "DayOfWeek": [int(features.day_of_week)],
            "Month": [int(features.month)],
            "DayOfMonth": [int(features.day_of_month)],
            "Lag1": [float(features.lag_1)],
            "Lag7": [float(features.lag_7)],
            "Lag14": [float(features.lag_14)],
            "Lag28": [float(features.lag_28)],
            "RollingMean7": [float(features.rolling_mean_7)],
            "RollingMean28": [float(features.rolling_mean_28)],
        }
        X_df = pd.DataFrame(input_data)

        # Informational warnings
        warnings = []
        if self.frequent_skus and sku not in self.frequent_skus:
            warnings.append(
                f"StockCode '{sku}' is outside the top-50 training categories; "
                "processed using infrequent category indicator (robust inference)."
            )

        predictions: Dict[str, float] = {}
        horizon_details: List[HorizonPredictionDetail] = []

        models_meta = self.metadata.get("models", {})

        for h in requested_horizons:
            pipeline = self.models.get(h)
            if pipeline is None:
                raise RuntimeError(f"Forecasting pipeline for horizon D_{h} is not available in registry.")

            # Generate prediction using fitted pipeline
            raw_pred = pipeline.predict(X_df)
            val = float(raw_pred[0])

            # Enforce non-negativity and finite numerical guarantees
            if np.isnan(val) or np.isinf(val):
                raise RuntimeError(f"Prediction for horizon D_{h} returned non-finite value: {val}")
            
            clean_pred = max(0.0, val)
            rounded_pred = round(clean_pred, 4)
            predictions[str(h)] = rounded_pred

            # Look up model info from metadata
            h_meta = models_meta.get(f"D_{h}", {})
            model_name = h_meta.get("selected_model", f"Model_D_{h}")
            wape = h_meta.get("best_metrics", {}).get("wape")

            horizon_details.append(
                HorizonPredictionDetail(
                    horizon_days=h,
                    predicted_demand=rounded_pred,
                    model_name=model_name,
                    wape=round(wape, 2) if wape is not None else None
                )
            )

        primary_h = requested_horizons[0]
        primary_val = predictions.get(str(primary_h))

        return ForecastResponse(
            stock_code=sku,
            horizons=requested_horizons,
            predictions=predictions,
            horizon_details=horizon_details,
            units="units",
            model_version=self.metadata.get("milestone", "Phase 1 v1.0"),
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            warnings=warnings,
            status="success",
            total_predicted_demand=primary_val,
            horizon_days=primary_h if len(requested_horizons) == 1 else None
        )

    def get_supported_horizons(self) -> Dict[str, Any]:
        """Returns the list and operational definition of supported forecast horizons."""
        return {
            "supported_horizons_days": self.supported_horizons,
            "description": "Multi-horizon retail demand planning windows (7 to 90 days).",
            "horizon_definitions": {
                "7": "Weekly fast-moving replenishment & shelf restock",
                "15": "Bi-weekly supplier batch ordering",
                "30": "Monthly inventory planning & space allocation",
                "90": "Quarterly supplier volume quotas & supply chain planning"
            }
        }

    def get_model_metrics(self) -> Dict[str, Any]:
        """Returns documented evaluation metrics and out-of-time benchmark results."""
        self.ensure_loaded()
        return {
            "project": self.metadata.get("project", "NEXORA"),
            "milestone": self.metadata.get("milestone", "Phase 1"),
            "dataset_reference": self.metadata.get("dataset_reference", "ml_feature_dataset.csv"),
            "training_timestamp": self.metadata.get("training_timestamp", "Unknown"),
            "encoding_strategy": self.metadata.get("encoding_strategy", "OneHotEncoder(max_categories=50)"),
            "backtesting_strategy": self.metadata.get("backtesting_strategy", "Single chronological out-of-time holdout"),
            "models": self.metadata.get("models", {})
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Returns runtime model architecture, loaded pipelines, and feature specifications."""
        self.ensure_loaded()
        active_models = {}
        for h, model in self.models.items():
            active_models[f"D_{h}"] = type(model.named_steps.get("regressor", model)).__name__

        return {
            "project": self.metadata.get("project", "NEXORA"),
            "version": "1.0.0",
            "status": "ready" if self.is_loaded else "uninitialized",
            "python_version": self.metadata.get("python_version", "3.11.9"),
            "scikit_learn_version": self.metadata.get("scikit_learn_version", "1.9.1"),
            "supported_horizons": self.supported_horizons,
            "active_models": active_models,
            "feature_columns": self.metadata.get("feature_columns", []),
            "categorical_columns": self.metadata.get("categorical_columns", ["StockCode"]),
            "numerical_columns": self.metadata.get("numerical_columns", []),
            "unseen_sku_handling": "OneHotEncoder infrequent category mapping (scikit-learn native)"
        }


# Global singleton instance
prediction_service = PredictionService()
