import subprocess

ps_code = """
$p = Get-Process -Id 274388 -ErrorAction SilentlyContinue
$w = Get-WmiObject Win32_Process -Filter "ProcessId = 274388"
[PSCustomObject]@{
    Id = $p.Id
    ProcessName = $p.ProcessName
    CommandLine = $w.CommandLine
    ParentId = $w.ParentProcessId
} | ConvertTo-Json
"""
try:
    out = subprocess.check_output(["powershell", "-Command", ps_code]).decode()
    print("Parent Info:")
    print(out)
except Exception as e:
    print("Error:", e)
