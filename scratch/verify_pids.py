import subprocess
import json

ps_code = """
$ids = @(259816, 274388, 86964)
Get-WmiObject Win32_Process | Where-Object { $ids -contains $_.ProcessId } | ForEach-Object {
    $p = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        Id = $_.ProcessId
        ProcessName = $_.Name
        ExecutablePath = $_.ExecutablePath
        CommandLine = $_.CommandLine
        ParentProcessId = $_.ParentProcessId
    }
} | ConvertTo-Json
"""

out = subprocess.check_output(["powershell", "-Command", ps_code]).decode()
print("PROCESS IDENTITIES:")
print(out)

net_out = subprocess.check_output("netstat -ano", shell=True).decode()
for line in net_out.splitlines():
    if ":8000 " in line and "LISTENING" in line:
        print("PORT 8000 LISTENER:", line)
