import subprocess

ps_code = """
$p = Get-Process -Id 259816
$w = Get-WmiObject Win32_Process -Filter "ProcessId = 259816"
[PSCustomObject]@{
    Id = $p.Id
    CommandLine = $w.CommandLine
    ParentId = $w.ParentProcessId
} | ConvertTo-Json
"""
try:
    out = subprocess.check_output(["powershell", "-Command", ps_code]).decode()
    print("WMIC Process Info:")
    print(out)
except Exception as e:
    print("Error:", e)
