import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MODULES = [
    "orbit_demo.py",
    "link.py",
    "power.py",
    "latency.py",
]

ORBIT_DIR = ROOT / "src" / "orbit"

def main():
    print("\n===================================")
    print(" FLOODSENTINEL ORBIT SYSTEM RUNNER")
    print("===================================\n")

    for module in MODULES:
        module_path = ORBIT_DIR / module

        print(f"\nRunning {module}...")
        result = subprocess.run(
            [sys.executable, str(module_path)],
            cwd=ROOT
        )

        if result.returncode != 0:
            print(f"\nERROR: {module} failed.")
            sys.exit(result.returncode)

        print(f"SUCCESS: {module} completed.")

    print("\n===================================")
    print(" ALL ORBIT MODULES COMPLETED!")
    print("===================================")

if __name__ == "__main__":
    main()