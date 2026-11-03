from pathlib import Path
import os,signal,subprocess
root=7115
cmd=Path(f'/proc/{root}/cmdline')
if cmd.exists():
 assert 'apk-source-1.2.38-20261024' in cmd.read_text().replace('\0',' ')
 pairs=[tuple(map(int,line.split())) for line in subprocess.check_output(['ps','-eo','pid=,ppid='],text=True).splitlines()]
 descendants=[root]
 for parent in descendants:
  descendants.extend(pid for pid,ppid in pairs if ppid==parent and pid not in descendants)
 for pid in reversed(descendants):
  try:os.kill(pid,signal.SIGTERM)
  except ProcessLookupError:pass
 print('Stopped current Android build:',descendants)
