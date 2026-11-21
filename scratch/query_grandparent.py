import subprocess

ps_code = """
$p = Get-Process -Id 94432 -ErrorAction SilentlyContinue
$w = Get-WmiObject Win32_Process -Filter "ProcessId = 94432"
[PSCustomObject]@{
    Id = $p.Id
    ProcessName = $p.ProcessName
    CommandLine = $w.CommandLine
    ParentId = $w.ParentProcessId
} | ConvertTo-Json
"""
try:
    out = subprocess.check_output(["powershell", "-Command", ps_code]).decode()
    print("Grandparent Info:")
    print(out)
except Exception as e:
    print("Error:", e)
