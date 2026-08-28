# Emmanuella's submitted attempt

The files in `submitted_configs/` preserve the exact CSV header and data rows
from the four case directories added in commit
`0a2f8fef8d906d6dbd4e3e2fa744b07591733833`. They are evidence, not runnable
recommendations, and must remain unchanged when the corrected workflow evolves.

The rest of her code and generated artifacts remain available exactly at that
Git commit. This avoids duplicating roughly 1,400 files and large binary model
outputs inside the current tree. Materialize the complete state with:

```bash
git worktree add ../SPEEDY-f77-emmanuella 0a2f8fef8d906d6dbd4e3e2fa744b07591733833
```

The critical driver change can be inspected directly with:

```bash
git diff 2f5b35c 0a2f8fe -- amlcs/amlcs_da.py
```

See the parent [`provenance/README.md`](../README.md) for the audit findings.
