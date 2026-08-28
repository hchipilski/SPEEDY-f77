# Audited Jack and Emmanuella workflows

This directory separates three things that had previously been mixed together:

1. **Jack's historical source** — the last Jack-authored repository state is
   immutable Git commit `2f5b35c4716ba86aea65c5479dc5879c9aba2e98`.
2. **Emmanuella's submitted attempt** — commit
   `0a2f8fef8d906d6dbd4e3e2fa744b07591733833`, including exact copies of the
   eight runner CSVs from her `case1` through `case4` directories, is recorded
   under [`provenance/emmanuella_attempt`](provenance/emmanuella_attempt/README.md).
3. **Audited report reconstruction** — corrected, portable runners for the
   eight selected method/case combinations live under
   [`jack_report`](jack_report/README.md).

The report reconstruction is not presented as a byte-for-byte directory that
Jack left behind. No such complete four-case runner directory exists in his
last commit. It is a documented reconstruction from his code history, archived
tuning results, and `Jacks_defense_report.pdf`.

See [`provenance/README.md`](provenance/README.md) for the evidence and the
specific errors identified in the submitted reproduction.
