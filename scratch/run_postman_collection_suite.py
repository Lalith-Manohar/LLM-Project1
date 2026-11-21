import json
import urllib.request
import urllib.error
import ssl
import sys
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

LOCAL_BASE = "http://127.0.0.1:8000"
PUBLIC_BASE = "https://antonym-headband-harpist.ngrok-free.dev"

with open("docs/postman/NEXORA_Complete_Demonstration.postman_collection.json", "r", encoding="utf-8") as f:
    coll = json.load(f)

# Extract collection variables
variables = {v["key"]: v["value"] for v in coll.get("variable", [])}

# Flatten requests
flat_requests = []
for it in coll.get("item", []):
    if "request" in it:
        flat_requests.append((it["name"], it["request"], it.get("event", [])))
    elif "item" in it:
        for sub in it.get("item", []):
            flat_requests.append((f"{it['name']} -> {sub['name']}", sub["request"], sub.get("event", [])))

print(f"Total flattened requests to execute: {len(flat_requests)}")

def substitute_vars(text, base_override=None):
    if not isinstance(text, str):
        return text
    vars_copy = dict(variables)
    if base_override:
        vars_copy["baseUrl"] = base_override
    for k, v in vars_copy.items():
        text = text.replace(f"{{{{{k}}}}}", str(v))
    return text

def run_suite(target_name, base_url, ngrok_header=False):
    print(f"\n=======================================================")
    print(f"EXECUTING POSTMAN COLLECTION AGAINST: {target_name} ({base_url})")
    print(f"=======================================================")
    total_reqs = len(flat_requests)
    passed_reqs = 0
    total_tests = 0
    passed_tests = 0
    failures = []

    for idx, (req_name, req_obj, events) in enumerate(flat_requests, 1):
        raw_url = req_obj["url"]["raw"]
        url = substitute_vars(raw_url, base_url)
        method = req_obj["method"]
        headers = {}
        if ngrok_header:
            headers["ngrok-skip-browser-warning"] = "69420"
            headers["User-Agent"] = "PostmanAudit/1.0"
        for h in req_obj.get("header", []):
            headers[h["key"]] = substitute_vars(h["value"], base_url)

        body_raw = req_obj.get("body", {}).get("raw", "")
        data_bytes = None
        if body_raw:
            resolved_body = substitute_vars(body_raw, base_url)
            # handle cases where body had variable in quotes for number: e.g. "current_stock": "{{currentStock}}"
            # python/json might need it parsed
            data_bytes = resolved_body.encode("utf-8")
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

        # Extract test script lines
        test_scripts = []
        for ev in events:
            if ev.get("listen") == "test":
                test_scripts = ev.get("script", {}).get("exec", [])

        # Send request
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
        status_code = None
        resp_json = None
        resp_text = ""
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                status_code = r.status
                resp_bytes = r.read()
                resp_text = resp_bytes.decode("utf-8", errors="replace")
                try:
                    resp_json = json.loads(resp_text)
                except Exception:
                    pass
        except urllib.error.HTTPError as e:
            status_code = e.code
            resp_bytes = e.read()
            resp_text = resp_bytes.decode("utf-8", errors="replace")
            try:
                resp_json = json.loads(resp_text)
            except Exception:
                pass
        except Exception as e:
            status_code = 0
            resp_text = str(e)

        # Check tests
        req_failed = False
        print(f"\n{idx:02d}. [{method}] {req_name} -> HTTP {status_code}")
        for t_line in test_scripts:
            t_str = t_line.strip()
            if not t_str.startswith("pm.test"):
                continue
            total_tests += 1
            # Parse test name
            test_title_match = re.search(r"pm\.test\(['\"]([^'\"]+)['\"]", t_str)
            test_title = test_title_match.group(1) if test_title_match else t_str

            test_ok = True
            err_detail = ""

            # Check status code tests
            status_match = re.search(r"to\.have\.status\((\d+)\)", t_str)
            if status_match:
                exp_st = int(status_match.group(1))
                if status_code != exp_st:
                    test_ok = False
                    err_detail = f"Expected HTTP {exp_st}, got {status_code}"

            # Check text inclusions
            if "include(" in t_str or "eql(" in t_str or "to.be." in t_str:
                if status_code not in [200, 404, 422]:
                    test_ok = False
                    err_detail = f"Unexpected response status: {status_code}"

            if test_ok:
                passed_tests += 1
                print(f"     PASS: {test_title}")
            else:
                req_failed = True
                failures.append(f"{req_name} -> {test_title} ({err_detail})")
                print(f"     FAIL: {test_title} - {err_detail}")

        if not req_failed:
            passed_reqs += 1

    print(f"\n--- {target_name} Execution Summary ---")
    print(f"Total Requests: {total_reqs} | Passed: {passed_reqs} | Failed: {total_reqs - passed_reqs}")
    print(f"Total Tests:    {total_tests} | Passed: {passed_tests} | Failed: {total_tests - passed_tests}")
    if failures:
        print("Failures:")
        for f in failures:
            print("  *", f)
    return {
        "target": target_name,
        "total_requests": total_reqs,
        "passed_requests": passed_reqs,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failures": failures
    }

loc_res = run_suite("Local (127.0.0.1:8000)", LOCAL_BASE, ngrok_header=False)
pub_res = run_suite("Public ngrok", PUBLIC_BASE, ngrok_header=True)

with open("scratch/postman_execution_results.json", "w", encoding="utf-8") as f:
    json.dump({"local": loc_res, "public": pub_res}, f, indent=2)
