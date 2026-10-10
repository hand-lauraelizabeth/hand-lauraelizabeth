"""Documentation-only QA plan checks (not device tests)."""
from pathlib import Path
doc = (Path(__file__).resolve().parents[1] / "SPRINT2_DEVICE_QA_AND_ROLLBACK.md").read_text()
cases = [line.split("|")[1].strip() for line in doc.splitlines() if line.startswith("| D")]
assert cases == [f"D{i:02}" for i in range(1, 24)]
for required in ("6,243", "531", "781", "306", "4,999", "5,000", "14,999", "15,000",
                 "24 → 48 → 72", "physical iOS Safari", "physical Android Chrome",
                 "Draft 1154", "1044", "NOT RUN", "BLOCKED", "fresh explicit owner approval"):
    assert required in doc, required
print("SPRINT2_DEVICE_QA_DOCUMENTATION_PASS", len(cases))
