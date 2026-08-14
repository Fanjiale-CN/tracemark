#!/usr/bin/env python3
"""Run all example cases and output to examples/<case>/output.png."""
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

cases = sorted(glob.glob(os.path.join(ROOT, "examples", "*", "config.yaml")))
if not cases:
    print("[tracemark] no examples found", file=sys.stderr)
    sys.exit(1)

failed = 0
for cfg in cases:
    case_dir = os.path.dirname(cfg)
    out = os.path.join(case_dir, "output.png")
    r = subprocess.run(["python3", os.path.join(ROOT, "scripts", "render.py"),
                        "--config", cfg, "--out", out], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL {case_dir}:\n{r.stdout}\n{r.stderr}")
        failed += 1
    else:
        print(f"ok   {case_dir}")

sys.exit(1 if failed else 0)
