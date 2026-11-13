## Summary

Describe the change, intended audience, affected project or tool, and minimum useful release scope.

Existing feature PR / dependency links:
- 
Does this replace or overlap an open PR? Explain the relationship before opening another.

## Verification

- [ ] Relevant tests pass on the **exact head commit**; include commands, results, and commit SHA.
- [ ] Changed behavior and recoverable errors were exercised (or explicitly identify what remains untested).
- [ ] Keyboard, narrow-screen/reflow, accessibility, and privacy checks appropriate to this change are documented.
- [ ] Data provenance, source vintage, uncertainty, and synthetic fixtures are identified where applicable.
- [ ] Public links point to the actual source; related models are not presented as identical artifacts.
- [ ] Any failed, pending, unrelated, or unperformed checks are distinguished from passing checks.

## Release authorization and state

- Current state: Draft / Ready for review / Approved for merge / Published (choose one).
- Exact item-specific authorization for merge or publication (link or "not yet granted"):
- Production WordPress page and deployed version, if applicable:
- Does this change expose private evidence, real request records, or sensitive user inputs? If so, stop and document the review gate privately.

**A green CI run or an approved PR does not itself authorize publication.** Keep production unchanged until the exact item has release authorization. Do not close, delete, force-push, or merge an older PR merely because it is old or appears duplicative; inspect its work and dependencies first.

## Risks and rollback

Document compatibility concerns, unresolved blockers, data limitations, affected integrations, and a safe rollback path. Distinguish an existing repository-wide failure from a regression introduced by this head commit.
