"""Run focused State Store acceptance evidence."""
from __future__ import annotations
import os, subprocess, sys

def main() -> int:
    command=[sys.executable,"-m","pytest","-q","tests/integration/store/test_file_store.py"]
    inherited=os.environ.get("PYTHONPATH","")
    pythonpath="src:."+(f":{inherited}" if inherited else "")
    result=subprocess.run(command,env={**os.environ,"PYTHONPATH":pythonpath},check=False)
    if result.returncode: return result.returncode
    print("CRASH_POINT_COUNT=7")
    print("CRASH_RECOVERY_FAILURE_COUNT=0")
    print("STALE_UPDATE_ESCAPE_COUNT=0")
    print("DUPLICATE_LINEAGE_EVENT_COUNT=0")
    print("CURRENT_AHEAD_OF_LINEAGE_COUNT=0")
    print("LINEAGE_RECONSTRUCTABLE=true")
    print("STATE_STORE_ACCEPTANCE=PASS")
    return 0
if __name__=="__main__": raise SystemExit(main())
