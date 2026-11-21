import json
from pathlib import Path

collection = {
    "info": {
        "_postman_id": "nexora-complete-demo-v1",
        "name": "NEXORA Complete API Demonstration Suite (Forecasting & Inventory)",
        "description": (
            "# NEXORA — Academic & Technical Demonstration Suite\n\n"
            "This Postman collection provides a complete, end-to-end evaluation suite for the NEXORA "
            "Retail Management & Intelligence Web Platform. It demonstrates multi-horizon demand forecasting, "
            "rigorous API error handling, and explainable inventory replenishment recommendations.\n\n"
            "### Real-World Operational Workflow:\n"
            "1. **Health & Readiness:** Verify that the FastAPI backend process, machine learning models, and historical sales datasets are online.\n"
            "2. **Demand Forecasting:** Submit product SKUs to evaluate predicted customer demand across 7, 15, 30, and 90-day operational windows.\n"
            "3. **Inventory Replenishment:** Enter on-hand stock and supplier lead times to calculate exact replenishment quantities with transparent formulas.\n"
            "4. **Error & Boundary Validation:** Verify robust validation handling for unknown products (404), insufficient history (422), and negative stock (422).\n\n"
            "### Core Decision Support Formula:\n"
            "- `Coverage Window = Lead Time Days + Review Period Days`\n"
            "- `Forecast Demand = Multi-Horizon Interpolated Demand across Coverage Window`\n"
            "- `Daily Demand Rate = Forecast Demand / Coverage Window`\n"
            "- `Safety Stock = Daily Demand Rate * Safety Stock Days`\n"
            "- `Target Stock = Forecast Demand + Safety Stock`\n"
            "- `Recommended Purchase Quantity = max(0, Target Stock - Current Stock)`\n\n"
            "**Note:** NEXORA provides empirical decision support recommendations for warehouse managers. "
            "It does not unilaterally place automated orders with external vendors."
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "variable": [
        {"key": "baseUrl", "value": "http://127.0.0.1:8000", "type": "string"},
        {"key": "testSku1", "value": "85123A", "type": "string"},
        {"key": "testSku2", "value": "22423", "type": "string"},
        {"key": "unknownSku", "value": "NON_EXISTENT_SKU_99999", "type": "string"},
        {"key": "insufficientHistorySku", "value": "20877", "type": "string"},
        {"key": "currentStock", "value": "50.0", "type": "string"},
        {"key": "leadTimeDays", "value": "7", "type": "string"},
        {"key": "reviewPeriodDays", "value": "7", "type": "string"},
        {"key": "safetyStockDays", "value": "3.0", "type": "string"}
    ],
    "item": []
}

def make_request(name, method, url_path, description, headers=None, body=None, tests=None):
    if headers is None:
        headers = []
    headers.append({"key": "ngrok-skip-browser-warning", "value": "69420", "type": "text"})
    
    req_obj = {
        "method": method,
        "header": headers,
        "url": {
            "raw": "{{baseUrl}}" + url_path,
            "host": ["{{baseUrl}}"],
            "path": [p for p in url_path.split("/") if p]
        },
        "description": description
    }
    if body is not None:
        req_obj["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2) if isinstance(body, dict) else body,
            "options": {"raw": {"language": "json"}}
        }
        headers.append({"key": "Content-Type", "value": "application/json", "type": "text"})

    item_obj = {
        "name": name,
        "request": req_obj
    }
    if tests:
        item_obj["event"] = [{
            "listen": "test",
            "script": {
                "exec": tests,
                "type": "text/javascript"
            }
        }]
    return item_obj

# -------------------------------------------------------------
# PART A: 12 Core Requests
# -------------------------------------------------------------
core_items = []

# 01. Liveness Probe
core_items.append(make_request(
    name="01. Liveness Probe (GET /health)",
    method="GET",
    url_path="/health",
    description="Verifies that the FastAPI application process is alive and responding.",
    tests=[
        "pm.test('Status code is 200', function () { pm.response.to.have.status(200); });",
        "pm.test('Status is healthy', function () { var jsonData = pm.response.json(); pm.expect(jsonData.status).to.eql('healthy'); });",
        "pm.test('Service is backend', function () { var jsonData = pm.response.json(); pm.expect(jsonData.service).to.eql('backend'); });",
        "pm.test('Response time is under 2000ms', function () { pm.expect(pm.response.responseTime).to.be.below(2000); });"
    ]
))

# 02. Readiness Probe
core_items.append(make_request(
    name="02. Readiness Probe (GET /ready)",
    method="GET",
    url_path="/ready",
    description="Probes whether machine learning model pipelines and historical datasets are indexed and ready for inference.",
    tests=[
        "pm.test('Status code is 200', function () { pm.response.to.have.status(200); });",
        "pm.test('System status is ready', function () { var jsonData = pm.response.json(); pm.expect(jsonData.status).to.eql('ready'); });",
        "pm.test('Models subsystem is ready', function () { var jsonData = pm.response.json(); pm.expect(jsonData.models.ready).to.be.true; });",
        "pm.test('Historical data is ready', function () { var jsonData = pm.response.json(); pm.expect(jsonData.historical_data.ready).to.be.true; });"
    ]
))

# 03. API Readiness Alias
core_items.append(make_request(
    name="03. API Readiness (GET /api/v1/ready)",
    method="GET",
    url_path="/api/v1/ready",
    description="API v1 prefix route alias confirming subsystem readiness under the /api/v1/ routing namespace.",
    tests=[
        "pm.test('Status code is 200', function () { pm.response.to.have.status(200); });",
        "pm.test('System status is ready', function () { var jsonData = pm.response.json(); pm.expect(jsonData.status).to.eql('ready'); });",
        "pm.test('Subsystems verified ready', function () { var jsonData = pm.response.json(); pm.expect(jsonData.models.ready).to.be.true; pm.expect(jsonData.historical_data.ready).to.be.true; });"
    ]
))

# 04. Supported Forecast Horizons
core_items.append(make_request(
    name="04. Supported Forecast Horizons (GET /api/v1/forecast/horizons)",
    method="GET",
    url_path="/api/v1/forecast/horizons",
    description="Returns the business definitions and supported forecast horizons (7, 15, 30, and 90 days).",
    tests=[
        "pm.test('Status code is 200', function () { pm.response.to.have.status(200); });",
        "pm.test('Supported horizons match [7, 15, 30, 90]', function () { var jsonData = pm.response.json(); pm.expect(jsonData.supported_horizons_days).to.eql([7, 15, 30, 90]); });",
        "pm.test('Horizon definitions present', function () { var jsonData = pm.response.json(); pm.expect(jsonData.horizon_definitions).to.have.property('7'); pm.expect(jsonData.horizon_definitions).to.have.property('30'); });"
    ]
))

# 05. Valid Forecast — Short-Term
core_items.append(make_request(
    name="05. Valid Forecast — Short-Term (POST /api/v1/forecast/predict)",
    method="POST",
    url_path="/api/v1/forecast/predict",
    description="Submits high-volume SKU {{testSku1}} requesting exclusively the 7-day operational replenishment horizon.",
    body={
        "stock_code": "{{testSku1}}",
        "horizons": [7]
    },
    tests=[
        "pm.test('Status code is 200', function () { pm.response.to.have.status(200); });",
        "pm.test('Returns predictions dictionary', function () { var jsonData = pm.response.json(); pm.expect(jsonData).to.have.property('predictions'); pm.expect(jsonData.predictions).to.have.property('7'); });",
        "pm.test('7-day prediction is non-negative', function () { var jsonData = pm.response.json(); pm.expect(jsonData.predictions['7']).to.be.at.least(0); });",
        "pm.test('Stock code echoes correctly', function () { var jsonData = pm.response.json(); pm.expect(jsonData.stock_code).to.eql(pm.collectionVariables.get('testSku1')); });"
    ]
))

# 06. Valid Forecast — Multi-Horizon
core_items.append(make_request(
    name="06. Valid Forecast — Multi-Horizon (POST /api/v1/forecast/predict)",
    method="POST",
    url_path="/api/v1/forecast/predict",
    description="Submits SKU {{testSku1}} requesting all four standard horizons (7, 15, 30, and 90 days).",
    body={
        "stock_code": "{{testSku1}}",
        "horizons": [7, 15, 30, 90]
    },
    tests=[
        "pm.test('Status code is 200', function () { pm.response.to.have.status(200); });",
        "pm.test('All four horizons predicted', function () { var jsonData = pm.response.json(); pm.expect(jsonData.predictions).to.have.property('7'); pm.expect(jsonData.predictions).to.have.property('15'); pm.expect(jsonData.predictions).to.have.property('30'); pm.expect(jsonData.predictions).to.have.property('90'); });",
        "pm.test('All horizon predictions non-negative', function () { var jsonData = pm.response.json(); ['7', '15', '30', '90'].forEach(function(h) { pm.expect(jsonData.predictions[h]).to.be.at.least(0); }); });"
    ]
))

# 07. Second Product Forecast
core_items.append(make_request(
    name="07. Second Product Forecast (POST /api/v1/forecast/predict)",
    method="POST",
    url_path="/api/v1/forecast/predict",
    description="Submits a second verified commercial SKU {{testSku2}} to demonstrate multi-product catalog generalization.",
    body={
        "stock_code": "{{testSku2}}",
        "horizons": [7, 15, 30, 90]
    },
    tests=[
        "pm.test('Status code is 200', function () { pm.response.to.have.status(200); });",
        "pm.test('Stock code matches second SKU', function () { var jsonData = pm.response.json(); pm.expect(jsonData.stock_code).to.eql(pm.collectionVariables.get('testSku2')); });",
        "pm.test('Predictions returned successfully', function () { var jsonData = pm.response.json(); pm.expect(jsonData.predictions['7']).to.be.at.least(0); pm.expect(jsonData.predictions['30']).to.be.at.least(0); });"
    ]
))

# 08. Unknown SKU Error
core_items.append(make_request(
    name="08. Unknown SKU Error (POST /api/v1/forecast/predict)",
    method="POST",
    url_path="/api/v1/forecast/predict",
    description="Submits nonexistent SKU {{unknownSku}} to demonstrate proper HTTP 404 catalog not found error handling.",
    body={
        "stock_code": "{{unknownSku}}",
        "horizons": [7, 15, 30, 90]
    },
    tests=[
        "pm.test('Status code is 404', function () { pm.response.to.have.status(404); });",
        "pm.test('Detail indicates SKU not found', function () { var jsonData = pm.response.json(); pm.expect(jsonData.detail.toLowerCase()).to.include('not found'); });"
    ]
))

# 09. Genuine Insufficient History Error
core_items.append(make_request(
    name="09. Genuine Insufficient History Error (POST /api/v1/forecast/predict)",
    method="POST",
    url_path="/api/v1/forecast/predict",
    description="Submits SKU {{insufficientHistorySku}} (which has only 9 calendar days of sales history in the catalog) to demonstrate HTTP 422 validation failure.",
    body={
        "stock_code": "{{insufficientHistorySku}}",
        "horizons": [7, 15, 30, 90]
    },
    tests=[
        "pm.test('Status code is 422', function () { pm.response.to.have.status(422); });",
        "pm.test('Detail explains insufficient historical sales data', function () { var jsonData = pm.response.json(); pm.expect(jsonData.detail).to.include('Insufficient historical sales data'); });"
    ]
))

# 10. Invalid Request Validation
core_items.append(make_request(
    name="10. Invalid Request Validation (POST /api/v1/forecast/predict)",
    method="POST",
    url_path="/api/v1/forecast/predict",
    description="Submits an unsupported forecasting horizon [999] to demonstrate schema validation rejection.",
    body={
        "stock_code": "{{testSku1}}",
        "horizons": [999]
    },
    tests=[
        "pm.test('Status code is 422', function () { pm.response.to.have.status(422); });",
        "pm.test('Error reports unsupported horizon', function () { var jsonData = pm.response.json(); pm.expect(JSON.stringify(jsonData)).to.include('Unsupported forecast horizon'); });"
    ]
))

# 11. Missing Required Field
core_items.append(make_request(
    name="11. Missing Required Field (POST /api/v1/forecast/predict)",
    method="POST",
    url_path="/api/v1/forecast/predict",
    description="Sends an empty JSON payload omitting mandatory field stock_code to demonstrate Pydantic validation failure.",
    body={},
    tests=[
        "pm.test('Status code is 422', function () { pm.response.to.have.status(422); });",
        "pm.test('Validation detail reports missing stock_code', function () { var jsonData = pm.response.json(); pm.expect(JSON.stringify(jsonData)).to.include('stock_code'); });"
    ]
))

# 12. Invalid Endpoint / Not Found
core_items.append(make_request(
    name="12. Invalid Endpoint / Not Found (GET /api/v1/nonexistent-endpoint-xyz)",
    method="GET",
    url_path="/api/v1/nonexistent-endpoint-xyz",
    description="Requests a deliberately nonexistent API endpoint to demonstrate HTTP 404 routing error response.",
    tests=[
        "pm.test('Status code is 404', function () { pm.response.to.have.status(404); });",
        "pm.test('Detail indicates route not found', function () { var jsonData = pm.response.json(); pm.expect(jsonData.detail.toLowerCase()).to.include('not found'); });"
    ]
))

collection["item"].extend(core_items)

# -------------------------------------------------------------
# PART C: Additional Postman Inventory Requests
# -------------------------------------------------------------
inventory_folder = {
    "name": "Inventory Purchase Recommendations",
    "description": (
        "Endpoints for calculating explainable inventory replenishment directives, target stock levels, "
        "and purchase orders based on lead times, review cycles, and safety stock days."
    ),
    "item": []
}

# I01. Stock Purchase Recommendation — Low Stock
inventory_folder["item"].append(make_request(
    name="I01. Stock Purchase Recommendation — Low Stock",
    method="POST",
    url_path="/api/v1/inventory/recommend",
    description="Submits SKU {{testSku1}} with low current stock (50 units), demonstrating a positive purchase recommendation and risk alert.",
    body={
        "stock_code": "{{testSku1}}",
        "current_stock": "{{currentStock}}",
        "lead_time_days": "{{leadTimeDays}}",
        "review_period_days": "{{reviewPeriodDays}}",
        "safety_stock_days": "{{safetyStockDays}}"
    },
    tests=[
        "pm.test('Status code is 200', function () { pm.response.to.have.status(200); });",
        "pm.test('Recommended purchase quantity is positive', function () { var jsonData = pm.response.json(); pm.expect(jsonData.recommended_purchase_quantity).to.be.above(0); });",
        "pm.test('Stock condition indicates risk', function () { var jsonData = pm.response.json(); pm.expect(['CRITICAL', 'ELEVATED']).to.include(jsonData.stock_condition); });",
        "pm.test('Calculation explanation present', function () { var jsonData = pm.response.json(); pm.expect(jsonData.calculation_explanation).to.include('Coverage window of 14 days'); });"
    ]
))

# I02. Stock Purchase Recommendation — Sufficient Stock
inventory_folder["item"].append(make_request(
    name="I02. Stock Purchase Recommendation — Sufficient Stock",
    method="POST",
    url_path="/api/v1/inventory/recommend",
    description="Submits SKU {{testSku1}} with abundant current stock (50,000 units), demonstrating a purchase recommendation of exactly 0 and SAFE status.",
    body={
        "stock_code": "{{testSku1}}",
        "current_stock": 50000.0,
        "lead_time_days": 7,
        "review_period_days": 7,
        "safety_stock_days": 3.0
    },
    tests=[
        "pm.test('Status code is 200', function () { pm.response.to.have.status(200); });",
        "pm.test('Recommended purchase quantity is exactly 0', function () { var jsonData = pm.response.json(); pm.expect(jsonData.recommended_purchase_quantity).to.eql(0); });",
        "pm.test('Stock condition is SAFE', function () { var jsonData = pm.response.json(); pm.expect(jsonData.stock_condition).to.eql('SAFE'); });",
        "pm.test('Recommendation states no reorder required', function () { var jsonData = pm.response.json(); pm.expect(jsonData.recommendation).to.include('No reorder required'); });"
    ]
))

# I03. Stock Purchase Recommendation — Zero Stock
inventory_folder["item"].append(make_request(
    name="I03. Stock Purchase Recommendation — Zero Stock",
    method="POST",
    url_path="/api/v1/inventory/recommend",
    description="Submits SKU {{testSku1}} with zero on-hand stock, demonstrating that recommended purchase quantity equals target stock.",
    body={
        "stock_code": "{{testSku1}}",
        "current_stock": 0.0,
        "lead_time_days": 7,
        "review_period_days": 7,
        "safety_stock_days": 3.0
    },
    tests=[
        "pm.test('Status code is 200', function () { pm.response.to.have.status(200); });",
        "pm.test('Purchase quantity equals target stock', function () { var jsonData = pm.response.json(); pm.expect(jsonData.recommended_purchase_quantity).to.eql(jsonData.target_stock); });",
        "pm.test('Stock condition is CRITICAL', function () { var jsonData = pm.response.json(); pm.expect(jsonData.stock_condition).to.eql('CRITICAL'); });"
    ]
))

# I04. Stock Purchase Recommendation — Different Lead Time
inventory_folder["item"].append(make_request(
    name="I04. Stock Purchase Recommendation — Different Lead Time",
    method="POST",
    url_path="/api/v1/inventory/recommend",
    description="Submits SKU {{testSku1}} with an extended 14-day supplier lead time (21-day total coverage), demonstrating how lead time increases target stock.",
    body={
        "stock_code": "{{testSku1}}",
        "current_stock": 200.0,
        "lead_time_days": 14,
        "review_period_days": 7,
        "safety_stock_days": 3.0
    },
    tests=[
        "pm.test('Status code is 200', function () { pm.response.to.have.status(200); });",
        "pm.test('Coverage period equals 21 days', function () { var jsonData = pm.response.json(); pm.expect(jsonData.coverage_period_days).to.eql(21); });",
        "pm.test('Forecast demand reflects 21-day coverage', function () { var jsonData = pm.response.json(); pm.expect(jsonData.forecast_demand).to.be.above(0); });",
        "pm.test('Purchase quantity calculated non-negative', function () { var jsonData = pm.response.json(); pm.expect(jsonData.recommended_purchase_quantity).to.be.at.least(0); });"
    ]
))

# I05. Invalid Stock Quantity
inventory_folder["item"].append(make_request(
    name="I05. Invalid Stock Quantity",
    method="POST",
    url_path="/api/v1/inventory/recommend",
    description="Submits negative current stock (-50) to demonstrate schema validation failure (HTTP 422).",
    body={
        "stock_code": "{{testSku1}}",
        "current_stock": -50.0,
        "lead_time_days": 7,
        "review_period_days": 7
    },
    tests=[
        "pm.test('Status code is 422', function () { pm.response.to.have.status(422); });",
        "pm.test('Validation error mentions current_stock', function () { var jsonData = pm.response.json(); pm.expect(JSON.stringify(jsonData)).to.include('current_stock'); });"
    ]
))

# I06. Unknown SKU Replenishment
inventory_folder["item"].append(make_request(
    name="I06. Unknown SKU Replenishment",
    method="POST",
    url_path="/api/v1/inventory/recommend",
    description="Submits unknown SKU {{unknownSku}} to demonstrate HTTP 404 catalog not found error handling in inventory recommendation.",
    body={
        "stock_code": "{{unknownSku}}",
        "current_stock": 100.0,
        "lead_time_days": 7,
        "review_period_days": 7
    },
    tests=[
        "pm.test('Status code is 404', function () { pm.response.to.have.status(404); });",
        "pm.test('Detail mentions SKU not found', function () { var jsonData = pm.response.json(); pm.expect(jsonData.detail.toLowerCase()).to.include('not found'); });"
    ]
))

# I07. Insufficient History for Replenishment
inventory_folder["item"].append(make_request(
    name="I07. Insufficient History for Replenishment",
    method="POST",
    url_path="/api/v1/inventory/recommend",
    description="Submits SKU {{insufficientHistorySku}} (only 9 calendar days) to demonstrate HTTP 422 error handling in inventory recommendation.",
    body={
        "stock_code": "{{insufficientHistorySku}}",
        "current_stock": 100.0,
        "lead_time_days": 7,
        "review_period_days": 7
    },
    tests=[
        "pm.test('Status code is 422', function () { pm.response.to.have.status(422); });",
        "pm.test('Detail mentions insufficient historical sales data', function () { var jsonData = pm.response.json(); pm.expect(jsonData.detail).to.include('Insufficient historical sales data'); });"
    ]
))

collection["item"].append(inventory_folder)

out_file = Path("docs/postman/NEXORA_Complete_Demonstration.postman_collection.json")
out_file.parent.mkdir(parents=True, exist_ok=True)
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(collection, f, indent=2)

print(f"Generated {out_file} successfully:")
print(f"  Core requests: {len(core_items)}")
print(f"  Inventory requests: {len(inventory_folder['item'])}")
print(f"  Total requests: {len(core_items) + len(inventory_folder['item'])}")
