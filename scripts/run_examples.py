#!/usr/bin/env python3
"""Run all example cases via the unified entry point and assert outcomes.

A case may opt in to an expected failure by setting `_expect` in its
config.yaml:
    _expect: fail      # missing-glyph / structural error (non-zero exit)
    _expect: reject    # AUP gate rejection (non-zero exit)
Cases without `_expect` must render successfully (exit 0).
"""
import glob
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY = os.path.join(ROOT, "scripts", "tracemark.py")
cases = sorted(glob.glob(os.path.join(ROOT, "examples", "*", "config.yaml")))
if not cases:
    print("[tracemark] no examples found", file=sys.stderr)
    sys.exit(1)

failed = 0
for cfg in cases:
    case_dir = os.path.dirname(cfg)
    out = os.path.join(case_dir, "output.jpg")
    with open(cfg) as f:
        data = yaml.safe_load(f) or {}
    expect = data.get("_expect")  # None | "fail" | "reject"
    r = subprocess.run([sys.executable, ENTRY, "render", "--config", cfg,
                        "--out", out], capture_output=True, text=True)
    ok_exit = (expect is None and r.returncode == 0)
    expect_fail = (expect in ("fail", "reject") and r.returncode != 0)
    if ok_exit:
        print(f"ok      {case_dir}")
    elif expect_fail:
        print(f"expected {expect} {case_dir}  (rejected as designed)")
    else:
        print(f"FAIL    {case_dir}: exit={r.returncode} (expected {expect})")
        print(r.stdout)
        print(r.stderr)
        failed += 1
sys.exit(1 if failed else 0)
