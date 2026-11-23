"""Inventory Replenishment & Purchasing Decision Support Service.

Translates machine learning demand forecasts into operational purchase order
recommendations based on lead times, review periods, and safety stock buffers.
"""

import datetime
from typing import Dict, Any
from app.schemas.inventory import (
    InventoryRecommendationRequest,
    InventoryRecommendationResponse
)
from app.schemas.forecast import ForecastRequest
from app.services.prediction_service import prediction_service
from app.services.experimental_prediction_service import experimental_prediction_service
from app.services.historical_data_service import (
    historical_data_service,
    HistoricalDataNotFoundError,
    InsufficientHistoryError
)


class InventoryService:
    """Service implementing inventory replenishment recommendations and safety stock formulas."""

    @staticmethod
    def interpolate_horizon_demand(predictions: Dict[int, float], days: int) -> float:
        """Interpolates cumulative demand for an arbitrary coverage window using multi-horizon models.
        
        Anchors directly to trained models at 7, 15, 30, and 90 days.
        Uses piecewise linear interpolation between adjacent model horizons to preserve
        learned demand curves, saturation, and seasonality without crude flat multipliers.
        """
        p7 = float(predictions.get(7, 0.0))
        p15 = float(predictions.get(15, p7 * (15.0 / 7.0)))
        p30 = float(predictions.get(30, p15 * (30.0 / 15.0)))
        p90 = float(predictions.get(90, p30 * (90.0 / 30.0)))

        if days <= 0:
            return 0.0
        if days == 7:
            return round(p7, 4)
        if days == 15:
            return round(p15, 4)
        if days == 30:
            return round(p30, 4)
        if days == 90:
            return round(p90, 4)

        if days < 7:
            daily_rate = p7 / 7.0
            return round(max(0.0, daily_rate * days), 4)
        elif 7 < days < 15:
            frac = (days - 7) / (15 - 7)
            return round(max(0.0, p7 + frac * (p15 - p7)), 4)
        elif 15 < days < 30:
            frac = (days - 15) / (30 - 15)
            return round(max(0.0, p15 + frac * (p30 - p15)), 4)
        elif 30 < days < 90:
            frac = (days - 30) / (90 - 30)
            return round(max(0.0, p30 + frac * (p90 - p30)), 4)
        else:  # days > 90
            daily_rate = p90 / 90.0
            return round(max(0.0, daily_rate * days), 4)

    def get_recommendation(
        self,
        request: InventoryRecommendationRequest
    ) -> InventoryRecommendationResponse:
        """Generates an explainable inventory replenishment recommendation.
        
        Args:
            request: Validated InventoryRecommendationRequest schema.
            
        Returns:
            InventoryRecommendationResponse: Comprehensive purchase decision support.
            
        Raises:
            HistoricalDataNotFoundError: If SKU does not exist in catalog.
            InsufficientHistoryError: If SKU has fewer than 29 days history.
        """
        sku = request.stock_code.strip()

        # 1. Validate SKU presence
        historical_data_service.ensure_loaded()
        if not historical_data_service.has_sku(sku):
            raise HistoricalDataNotFoundError(f"Product SKU '{sku}' not found in historical retail catalog.")

        # 2. Query demand forecast from ML model
        forecast_req = ForecastRequest(
            stock_code=sku,
            horizons=[7, 15, 30, 90]
        )

        if request.use_experimental:
            experimental_prediction_service.ensure_loaded()
            forecast_resp = experimental_prediction_service.get_forecast(forecast_req)
            model_used = f"Task 12 Experimental ({forecast_resp.model_version})"
        else:
            prediction_service.ensure_loaded()
            forecast_resp = prediction_service.get_forecast(forecast_req)
            model_used = f"Production Baseline ({forecast_resp.model_version})"

        pred_dict = {int(k): float(v) for k, v in forecast_resp.predictions.items()}

        # 3. Calculate coverage window and projected demand
        coverage_period_days = request.lead_time_days + request.review_period_days
        forecast_demand = self.interpolate_horizon_demand(pred_dict, coverage_period_days)
        daily_demand_rate = round(forecast_demand / coverage_period_days, 4)

        # 4. Calculate safety stock and target stock
        safety_stock = round(daily_demand_rate * request.safety_stock_days, 2)
        target_stock = round(forecast_demand + safety_stock, 2)

        # 5. Determine recommended purchase quantity (non-negative)
        recommended_purchase_quantity = max(0.0, round(target_stock - request.current_stock, 2))

        # 6. Classify stock risk condition (AGENTS.md Section 6)
        if request.current_stock < forecast_demand:
            stock_condition = "CRITICAL"
        elif request.current_stock < target_stock:
            stock_condition = "ELEVATED"
        else:
            stock_condition = "SAFE"

        # 7. Actionable directive and explanation
        if recommended_purchase_quantity > 0:
            recommendation = (
                f"Purchase {recommended_purchase_quantity:.0f} additional units to restore target inventory "
                f"and protect against stockout risk through the {coverage_period_days}-day replenishment cycle."
            )
        else:
            recommendation = (
                f"Current stock of {request.current_stock:.0f} units adequately covers projected demand ({forecast_demand:.0f} units) "
                f"and safety buffer ({safety_stock:.0f} units) through the {coverage_period_days}-day cycle. No reorder required."
            )

        explanation = (
            f"Coverage window of {coverage_period_days} days (lead time {request.lead_time_days}d + review period {request.review_period_days}d) "
            f"has projected demand of {forecast_demand:.2f} units (daily rate {daily_demand_rate:.2f} units/day). "
            f"Safety stock buffer of {request.safety_stock_days} days requires {safety_stock:.2f} units. "
            f"Target stock level is {target_stock:.2f} units ({forecast_demand:.2f} forecast + {safety_stock:.2f} safety stock). "
            f"With current stock of {request.current_stock:.2f} units, recommended purchase quantity is "
            f"max(0, {target_stock:.2f} - {request.current_stock:.2f}) = {recommended_purchase_quantity:.2f} units. "
            f"Stock condition: {stock_condition}."
        )

        return InventoryRecommendationResponse(
            stock_code=sku,
            current_stock=round(request.current_stock, 2),
            lead_time_days=request.lead_time_days,
            review_period_days=request.review_period_days,
            coverage_period_days=coverage_period_days,
            forecast_demand=round(forecast_demand, 2),
            daily_demand_rate=round(daily_demand_rate, 4),
            safety_stock_days=request.safety_stock_days,
            safety_stock=safety_stock,
            target_stock=target_stock,
            recommended_purchase_quantity=recommended_purchase_quantity,
            stock_condition=stock_condition,
            recommendation=recommendation,
            calculation_explanation=explanation,
            model_used=model_used,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )


inventory_service = InventoryService()
