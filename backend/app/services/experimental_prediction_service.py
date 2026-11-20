"""Experimental Prediction Service layer for Task 12 ML model lifecycle and inference.

This service maintains the in-memory registry of the four best-performing Task 12
forecasting pipelines (D_7, D_15, D_30, D_90) trained on the full 2-year Online Retail II
dataset with chronological TargetEncoder, point-in-time pricing, and restored 60-day coverage.
It runs alongside the baseline prediction service under /api/v1/experimental without
touching or altering baseline production models.
"""

import sys
import json
import joblib
import threading
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

# Ensure backend root is on sys.path for unpickling custom transformers/regressors
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure custom classes are discoverable if pickled as top-level or ml.src modules
try:
    import ml.src.target_encoder  # noqa: F401
    import ml.experiments.model_selection_task12  # noqa: F401
except ImportError:
    pass

from app.core.config import settings
from app.schemas.forecast import (
    ForecastRequest,
    ForecastResponse,
    HorizonPredictionDetail,
    SUPPORTED_HORIZONS
)
from app.services.historical_data_service import historical_data_service


class ExperimentalPredictionService:
    """Manages in-memory registry of Task 12 experimental forecasting pipelines."""

    def __init__(self, models_dir: Optional[str] = None):
        if models_dir:
            self.models_dir = Path(models_dir)
        else:
            self.models_dir = Path(getattr(settings, "EXPERIMENTAL_MODELS_DIR", str(BACKEND_DIR / "ml" / "models_task12")))

        self.models: Dict[int, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.is_loaded: bool = False
        self.load_error: Optional[str] = None
        self._lock = threading.Lock()
        self.supported_horizons: List[int] = list(SUPPORTED_HORIZONS)

    def load_models(self) -> None:
        """Loads all serialized Task 12 model binaries and metadata into memory.
        
        Validates artifact existence, integrity, and usability via dummy inference.
        
        Raises:
            FileNotFoundError: If required model binaries or metadata are missing.
            RuntimeError: If model loading fails, artifacts are corrupted, or usability checks fail.
        """
        with self._lock:
            print(f"[NEXORA ExperimentalPredictionService] Initializing Task 12 models from: {self.models_dir}...")
            self.is_loaded = False
            self.load_error = None

            if not self.models_dir.is_dir():
                err = f"Experimental model directory does not exist: {self.models_dir.name}"
                self.load_error = err
                raise FileNotFoundError(err)

            metadata_path = self.models_dir / "models_metadata.json"
            if not metadata_path.is_file():
                err = f"Experimental model metadata manifest missing: {metadata_path.name}"
                self.load_error = err
                raise FileNotFoundError(err)

            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            except Exception as e:
                err = f"Failed to parse experimental model metadata: {e}"
                self.load_error = err
                raise RuntimeError(err)

            # Dummy verification DataFrame matching exact 20-column contract
            dummy_eval_df = pd.DataFrame({
                "StockCode": ["85123A"],
                "date": [datetime.date(2011, 12, 9)],
                "DayOfWeek": [4],
                "Month": [12],
                "DayOfMonth": [9],
                "Lag1": [10.0],
                "Lag7": [10.0],
                "Lag14": [10.0],
                "Lag28": [10.0],
                "Lag60": [10.0],
                "RollingMean7": [10.0],
                "RollingMean14": [10.0],
                "RollingMean28": [10.0],
                "RollingMean60": [10.0],
                "RollingStd7": [1.0],
                "RollingStd28": [1.0],
                "ZeroFraction28": [0.0],
                "MomentumRatio": [0.9],
                "UnitPrice": [2.55],
                "Has60dHistory": [1.0]
            })

            loaded_models = {}
            for h in self.supported_horizons:
                model_filename = f"demand_model_{h}d.joblib"
                model_path = self.models_dir / model_filename

                if not model_path.is_file():
                    err = f"Required experimental model artifact missing for horizon D_{h}: {model_filename}"
                    self.load_error = err
                    raise FileNotFoundError(err)

                try:
                    pipeline = joblib.load(model_path)
                except Exception as e:
                    err = f"Corrupted or unreadable experimental model artifact for horizon D_{h}: {e}"
                    self.load_error = err
                    raise RuntimeError(err)

                if not hasattr(pipeline, "predict"):
                    err = f"Loaded object for horizon D_{h} does not have a predict method"
                    self.load_error = err
                    raise RuntimeError(err)

                # Active usability smoke test: verify pipeline execution and finite output
                try:
                    test_pred = pipeline.predict(dummy_eval_df)
                    if len(test_pred) != 1 or not np.isfinite(float(test_pred[0])):
                        err = f"Model usability test failed for horizon D_{h}: non-finite or invalid output"
                        self.load_error = err
                        raise RuntimeError(err)
                except Exception as e:
                    err = f"Model usability test failed for horizon D_{h}: {e}"
                    self.load_error = err
                    raise RuntimeError(err)

                loaded_models[h] = pipeline

            self.models = loaded_models
            self.is_loaded = True
            self.load_error = None

            print(
                f"[NEXORA ExperimentalPredictionService] Successfully loaded and verified {len(self.models)} "
                f"Task 12 experimental models ([D_7, D_15, D_30, D_90]) into memory."
            )

    def is_ready(self) -> bool:
        """Returns True if and only if all 4 Task 12 models are loaded and verified in memory,
        and the point-in-time price service is available."""
        models_ready = bool(self.is_loaded and len(self.models) == len(self.supported_horizons) and self.load_error is None)
        price_ready = False
        try:
            from app.services.historical_data_service import historical_data_service
            price_ready = historical_data_service.is_price_service_ready()
        except Exception:
            pass
        return models_ready and price_ready

    def get_status(self) -> Dict[str, Any]:
        """Returns structured subsystem status for readiness and diagnostic probes."""
        price_ready = False
        try:
            from app.services.historical_data_service import historical_data_service
            price_ready = historical_data_service.is_price_service_ready()
        except Exception:
            pass
        models_ready = bool(self.is_loaded and len(self.models) == len(self.supported_horizons) and self.load_error is None)
        err = self.load_error
        if models_ready and not price_ready:
            err = "Point-in-time price service is not ready"

        return {
            "ready": self.is_ready(),
            "models_count": len(self.models),
            "loaded_horizons": sorted(list(self.models.keys())),
            "models_dir": str(self.models_dir.name),
            "price_service_ready": price_ready,
            "error": err
        }

    def ensure_loaded(self) -> None:
        """Ensures models are loaded; triggers loading if uninitialized."""
        if not self.is_loaded:
            self.load_models()
        if not self.is_ready():
            raise RuntimeError(f"Experimental forecasting models are not ready: {self.load_error or 'uninitialized'}")

    def get_forecast(self, request: ForecastRequest) -> ForecastResponse:
        """Executes multi-horizon demand inference for a validated forecast request using Task 12 models.
        
        Args:
            request: Validated ForecastRequest schema.
            
        Returns:
            ForecastResponse: Multi-horizon prediction response with metadata.
            
        Raises:
            RuntimeError: If models are not loaded and cannot be found.
        """
        self.ensure_loaded()

        sku = request.stock_code.strip()
        features = request.features
        requested_horizons = request.horizons or self.supported_horizons

        observation_date: Optional[str] = None
        history_days: Optional[int] = None
        is_auto_generated: bool = False

        # When caller does not provide manual features, generate them automatically from dataset
        if features is None:
            features, context = historical_data_service.get_features_for_sku(sku)
            observation_date = context.get("observation_date")
            history_days = context.get("history_days")
            is_auto_generated = True

        # Parse observation date
        obs_date_obj: datetime.date
        if observation_date:
            try:
                obs_date_obj = datetime.date.fromisoformat(observation_date)
            except ValueError:
                obs_date_obj = datetime.date.today()
        else:
            obs_date_obj = datetime.date.today()

        # Build feature values with safe defaults and Task 12 fallback contracts
        dow = int(features.day_of_week) if features.day_of_week is not None else obs_date_obj.weekday()
        month = int(features.month) if features.month is not None else obs_date_obj.month
        dom = int(features.day_of_month) if features.day_of_month is not None else obs_date_obj.day

        lag1 = float(features.lag_1)
        lag7 = float(features.lag_7)
        lag14 = float(features.lag_14)
        lag28 = float(features.lag_28)
        lag60 = float(features.lag_60) if features.lag_60 is not None else lag28

        rm7 = float(features.rolling_mean_7)
        rm14 = float(features.rolling_mean_14) if features.rolling_mean_14 is not None else rm7
        rm28 = float(features.rolling_mean_28)
        rm60 = float(features.rolling_mean_60) if features.rolling_mean_60 is not None else rm28

        std7 = float(features.rolling_std_7) if features.rolling_std_7 is not None else 0.0
        std28 = float(features.rolling_std_28) if features.rolling_std_28 is not None else 0.0
        zf28 = float(features.zero_fraction_28) if features.zero_fraction_28 is not None else 0.0
        mom = float(features.momentum_ratio) if features.momentum_ratio is not None else round(rm7 / (rm28 + 1.0), 4)

        if features.unit_price is not None:
            price = float(features.unit_price)
        else:
            try:
                price = historical_data_service.get_unit_price(sku, as_of_date=obs_date_obj)
            except Exception as e:
                raise RuntimeError(f"Point-in-time price service is unavailable: {e}") from e

        if features.has_60d_history is not None:
            has_60d = float(features.has_60d_history)
        else:
            has_60d = 1.0 if features.lag_60 is not None else 0.0

        # Construct input DataFrame strictly adhering to the 20-column contract
        input_data = {
            "StockCode": [sku],
            "date": [obs_date_obj],
            "DayOfWeek": [dow],
            "Month": [month],
            "DayOfMonth": [dom],
            "Lag1": [lag1],
            "Lag7": [lag7],
            "Lag14": [lag14],
            "Lag28": [lag28],
            "Lag60": [lag60],
            "RollingMean7": [rm7],
            "RollingMean14": [rm14],
            "RollingMean28": [rm28],
            "RollingMean60": [rm60],
            "RollingStd7": [std7],
            "RollingStd28": [std28],
            "ZeroFraction28": [zf28],
            "MomentumRatio": [mom],
            "UnitPrice": [price],
            "Has60dHistory": [has_60d]
        }
        X_df = pd.DataFrame(input_data)

        # Informational warnings and context
        warnings = []
        if is_auto_generated and observation_date:
            warnings.append(
                f"Historical demand features automatically generated from {history_days} daily records "
                f"up to observation date {observation_date} (UCI Online Retail II 2-year recovered dataset)."
            )
        warnings.append("Experimental Task 12 ML models active (chronological TargetEncoder, PIT price, 2-year data).")

        predictions: Dict[str, float] = {}
        horizon_details: List[HorizonPredictionDetail] = []
        models_meta = self.metadata.get("models", {})

        for h in requested_horizons:
            pipeline = self.models.get(h)
            if pipeline is None:
                raise RuntimeError(f"Experimental forecasting pipeline for horizon D_{h} is not available.")

            # Generate prediction using fitted pipeline
            raw_pred = pipeline.predict(X_df)
            val = float(raw_pred[0])

            # Enforce non-negativity and finite numerical guarantees
            if np.isnan(val) or np.isinf(val):
                raise RuntimeError(f"Experimental prediction for horizon D_{h} returned non-finite value: {val}")

            clean_pred = max(0.0, val)
            rounded_pred = round(clean_pred, 4)
            predictions[str(h)] = rounded_pred

            # Look up model info from metadata
            h_meta = models_meta.get(f"D_{h}", {})
            model_name = h_meta.get("selected_model", f"Task12_Model_D_{h}")
            wape = h_meta.get("holdout_wape")

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
            model_version=f"Task 12 Experimental ({self.metadata.get('dataset_span', '2009-2011 2-year')})",
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            warnings=warnings,
            status="success",
            total_predicted_demand=primary_val,
            horizon_days=primary_h if len(requested_horizons) == 1 else None,
            observation_date=observation_date,
            history_days=history_days,
            is_auto_generated=is_auto_generated
        )

    def get_supported_horizons(self) -> Dict[str, Any]:
        """Returns the list and operational definition of supported forecast horizons."""
        return {
            "supported_horizons_days": self.supported_horizons,
            "description": "Multi-horizon retail demand planning windows (7 to 90 days) - Task 12 Experimental.",
            "models": {
                str(h): self.metadata.get("models", {}).get(f"D_{h}", {}).get("selected_model", f"Model_D_{h}")
                for h in self.supported_horizons
            },
            "horizon_definitions": {
                "7": "Weekly fast-moving replenishment & shelf restock (ElasticNet a=0.01, l1=0.8)",
                "15": "Bi-weekly supplier batch ordering (Residual Ridge alpha=100.0 on RollingMean28*15)",
                "30": "Monthly inventory planning & space allocation (Ridge alpha=100.0)",
                "90": "Quarterly supplier volume quotas & supply chain planning (Ridge alpha=100.0)"
            }
        }

    def get_model_metrics(self) -> Dict[str, Any]:
        """Returns documented evaluation metrics, CV results, and holdout benchmarks."""
        self.ensure_loaded()
        return {
            "project": self.metadata.get("project", "NEXORA Task 12"),
            "timestamp": self.metadata.get("timestamp", "Unknown"),
            "dataset_rows": self.metadata.get("dataset_rows", 1067371),
            "dataset_span": self.metadata.get("dataset_span", "2009-12-01 to 2011-12-09"),
            "cross_validation": self.metadata.get("cross_validation", "3-Fold DateGroupedTimeSeriesSplit"),
            "models": self.metadata.get("models", {})
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Returns runtime model architecture, loaded pipelines, and feature specifications."""
        self.ensure_loaded()
        active_models = {}
        for h, model in self.models.items():
            if hasattr(model, "named_steps"):
                reg = model.named_steps.get("regressor", model)
                active_models[f"D_{h}"] = type(reg).__name__
            elif hasattr(model, "estimator") and hasattr(model.estimator, "named_steps"):
                reg = model.estimator.named_steps.get("regressor", model.estimator)
                active_models[f"D_{h}"] = f"ResidualRegressor({type(reg).__name__})"
            else:
                active_models[f"D_{h}"] = type(model).__name__

        return {
            "project": self.metadata.get("project", "NEXORA Task 12 Experimental"),
            "version": "1.0.0-experimental",
            "status": "ready" if self.is_loaded else "uninitialized",
            "models_dir": str(self.models_dir.name),
            "supported_horizons": self.supported_horizons,
            "active_models": active_models,
            "feature_contract_columns_count": 20,
            "feature_columns": [
                "StockCode", "date", "DayOfWeek", "Month", "DayOfMonth",
                "Lag1", "Lag7", "Lag14", "Lag28", "Lag60",
                "RollingMean7", "RollingMean14", "RollingMean28", "RollingMean60",
                "RollingStd7", "RollingStd28", "ZeroFraction28", "MomentumRatio",
                "UnitPrice", "Has60dHistory"
            ],
            "encoding_strategy": "ChronologicalTargetEncoder (point-in-time cumulative mean, fallback to global mean)",
            "pricing_strategy": "Point-in-time historical median price per SKU"
        }


# Global singleton instance
experimental_prediction_service = ExperimentalPredictionService()
