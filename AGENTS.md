# AGENTS.md

Working rules for anyone changing this repository, people and agents alike.
How contracts are owned and changed is in [`GOVERNANCE.md`](GOVERNANCE.md);
compatibility in [`COMPATIBILITY.md`](COMPATIBILITY.md); adoption in
[`ADOPTION.md`](ADOPTION.md).

## Rules that do not change

1. **Collect the defects first, then fix.** Critical work has three phases.
   *Collection*: one or more independent readers search the whole class
   (every key, operation, format, path) without fixing anything, until it is
   exhausted. *Single fix*: whoever fixes receives the complete list and
   closes it by construction (one rule, a declarative table, enumeration
   tests), not with case-by-case patches. *Confirmation*: a single reading
   round on the list and on regressions. Never "find, fix, find, fix". After
   six reading rounds that still find defects, stop, change approach and
   tell the maintainer (maintainer rule, 2026-11-03).
