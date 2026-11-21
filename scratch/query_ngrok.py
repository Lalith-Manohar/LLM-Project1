import subprocess

ps_code = """
Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match "ngrok" } | ForEach-Object {
    [PSCustomObject]@{
        Id = $_.ProcessId
        Name = $_.Name
        CommandLine = $_.CommandLine
        ParentId = $_.ParentProcessId
    }
} | ConvertTo-Json
"""
try:
    out = subprocess.check_output(["powershell", "-Command", ps_code]).decode()
    print("NGROK Processes:")
    print(out)
except Exception as e:
    print("Error:", e)
