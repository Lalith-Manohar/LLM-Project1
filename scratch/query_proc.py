import subprocess
import json

pid = 259816
ps_cmd = f"Get-Process -Id {pid} | Select-Object Id, ProcessName, StartTime, Path | ConvertTo-Json"
try:
    out = subprocess.check_output(["powershell", "-Command", ps_cmd]).decode()
    print("Process Info:")
    print(out)
except Exception as e:
    print("Error querying powershell:", e)
