# SUNY STEP program review queue baseline — 2026-10-07

**Status:** PASS  
**Source agreements:** 528 current SUNY STEP records  
**Institution identity prerequisite:** 58 / 58 campus labels reviewed; both sides of 528 / 528 agreements resolved to current IPEDS institution identity.

The first source-preserving program review queue contains **692 unique review rows**:

- **385 sending-program rows**
- **307 receiving/destination-program rows**
- **571 rows with a conservatively parsed degree marker**
- **117 agreement rows with no destination-program text in the source**
- **0 automatically assigned CIP codes**

All 692 review IDs are unique. Every review row retains reviewed institution UNITID and exact STEP program wording.

## What this baseline does not mean

A parsed degree marker is not a program identity, and a similar program title is not a CIP crosswalk. The initial queue intentionally leaves CIP blank. Accepted mapping requires source-published CIP, an authoritative institution program identifier, or a separately reviewed program-name + award-level crosswalk.

This queue is the next review surface before transfer-program evidence is allowed into product-grain matching.

**Live workflow:** https://github.com/hand-lauraelizabeth/hand-lauraelizabeth/actions/runs/37637883090
