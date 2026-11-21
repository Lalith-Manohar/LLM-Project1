import urllib.request
import json

endpoints = ['/health', '/ready', '/docs', '/openapi.json']
for ep in endpoints:
    url = f'http://127.0.0.1:8000{ep}'
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = resp.read()
            print(f'=== {ep} === -> Status: {resp.status}, Size: {len(data)} bytes')
            if ep == '/health':
                print('  Body:', data.decode()[:200])
            elif ep == '/ready':
                j = json.loads(data.decode())
                print('  Status:', j.get('status'), '| Models ready:', j.get('models', {}).get('ready'), '| Data ready:', j.get('historical_data', {}).get('ready'))
            elif ep == '/openapi.json':
                j = json.loads(data.decode())
                paths = list(j.get('paths', {}).keys())
                print(f'  Total registered paths: {len(paths)}')
                print('  Has /api/v1/inventory/recommend:', '/api/v1/inventory/recommend' in paths)
                print('  Forecast paths count:', len([p for p in paths if 'forecast' in p]))
    except urllib.error.HTTPError as e:
        print(f'=== {ep} === -> HTTP Error: {e.code}')
    except Exception as e:
        print(f'=== {ep} === -> Error: {e}')
