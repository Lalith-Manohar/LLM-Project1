import urllib.request
import json

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/forecast/predict',
    data=json.dumps({'stock_code': '85123A', 'horizon_days': 7}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        print('Local Forecast API Status:', resp.status)
        print('Body:', resp.read().decode())
except Exception as e:
    print('Local Forecast API Error:', e)
