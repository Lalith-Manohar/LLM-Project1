import json

with open("scratch/task31_audit_results.json", "r", encoding="utf-8") as f:
    d = json.load(f)

inv = d["section6_inventory"]
for cid in ["I01_sku85123A_stock100", "I02_sku85123A_high_stock", "I03_sku85123A_zero_stock", "I04_sku85123A_longer_lead"]:
    res = inv[cid]["local_response"]
    print(f"\n==================== {cid} ====================")
    print(f"Current Stock: {res.get('current_stock')}")
    print(f"Lead Time / Review: {res.get('lead_time_days')}d / {res.get('review_period_days')}d -> Coverage: {res.get('coverage_period_days')}d")
    print(f"Forecast Demand: {res.get('forecast_demand')} (daily rate: {res.get('daily_demand_rate')})")
    print(f"Safety Stock ({res.get('safety_stock_days')}d): {res.get('safety_stock')}")
    print(f"Target Stock: {res.get('target_stock')}")
    print(f"Recommended Purchase Qty: {res.get('recommended_purchase_quantity')}")
    print(f"Stock Condition: {res.get('stock_condition')}")
    print(f"Recommendation: {res.get('recommendation')}")
