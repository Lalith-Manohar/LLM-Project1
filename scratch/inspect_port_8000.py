import subprocess
import re

out = subprocess.check_output('netstat -ano', shell=True).decode()
for line in out.splitlines():
    if ':8000 ' in line and 'LISTENING' in line:
        print('Netstat line:', line)
        parts = line.strip().split()
        pid = parts[-1]
        print('Owning PID:', pid)
        try:
            p_out = subprocess.check_output(['tasklist', '/fi', f'PID eq {pid}']).decode()
            print(p_out)
        except Exception as e:
            print('Could not query tasklist:', e)
        try:
            wmic_out = subprocess.check_output(['wmic', 'process', 'where', f'ProcessId={pid}', 'get', 'CommandLine,ExecutablePath']).decode()
            print(wmic_out)
        except Exception as e:
            print('Could not query wmic:', e)
