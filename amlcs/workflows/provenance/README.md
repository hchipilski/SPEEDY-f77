# Provenance audit

## Immutable source points

| Material | Commit | Author | Meaning |
| --- | --- | --- | --- |
| Original AMLCS baseline referenced by the repository | `37be4a51e050b984de06681f06517dd33a3f47a7` | jjs21b | Older baseline; not Jack's completed study |
| Jack source snapshot used for this reconstruction | `2f5b35c4716ba86aea65c5479dc5879c9aba2e98` | Jack Schwartz | Ancestor containing the DA core on which the corrected workflow is based |
| Later `testing-jack` branch head | `0c8b6ae4aca633005da82d1fcbc83ca6c8a7aa4d` | Jack Schwartz | 15 commits ahead; adds tuning, validation, and plotting artifacts without changing the three DA-core files |
| Emmanuella submission | `0a2f8fef8d906d6dbd4e3e2fa744b07591733833` | Emmanuella Ababio | Adds `case1`–`case4`, results, and the driver regression |

To inspect exact, read-only working trees without mixing either state into the
current branch, run from the repository root and choose unused destinations:

```bash
git worktree add ../SPEEDY-f77-jack 2f5b35c4716ba86aea65c5479dc5879c9aba2e98
git worktree add ../SPEEDY-f77-emmanuella 0a2f8fef8d906d6dbd4e3e2fa744b07591733833
```

The top-level `original-amlcs` and `testing-jack` entries are not usable source
copies. They were committed as Git links, but there is no `.gitmodules` file or
submodule URL. The `testing-jack` link targets Jack's later branch-head object
`0c8b6ae4aca633005da82d1fcbc83ca6c8a7aa4d`, which is not carried as an object
in this repository. This explains why both directories appear empty after
checkout. The object is available from Jack's separate repository at
<https://github.com/jjs21b/SPEEDY-f77/tree/testing-jack>.

Comparing the two Jack revisions confirms that `amlcs/amlcs_da.py`,
`amlcs/observation.py`, and `amlcs/sequential_methods.py` have identical Git
blob IDs. The 15 later commits therefore do not change the DA core used by the
four-case reconstruction; they supply additional experimental and
post-processing evidence.

## What went wrong in the reproduction

The primary error is directly established by the commit diff:

```bash
git diff 2f5b35c 0a2f8fe -- amlcs/amlcs_da.py
```

Emmanuella's commit removed the code that read `nonlinear_obs`, `scalefact`,
`wind_nonlinear_operator`, `normalize_nonlinear`, and
`nonlinear_operator_type`. It also stopped passing those values to
`observation(...)` and `sequential_method(...).get_instance(...)`. Therefore:

- case 2 CSVs said `nonlinear_obs=True`, but the driver constructed the default
  linear observation operator;
- the LETKF side of case 3 did not receive the wind-nonlinear flag or wind error
  values;
- the runs could complete without an exception while executing a materially
  different experiment.

A comparison with the older `original-amlcs` target (`37be4a51`) shows that
Emmanuella's submitted `amlcs_da.py` is that baseline driver, apart from adding
the mask number to the output-folder name. This strongly suggests that Jack's
enhanced driver was accidentally replaced while the case folders were being
assembled.

The submitted runner files introduced additional mismatches:

| Case | Submitted issue | Reported/archived selection |
| --- | --- | --- |
| 1, all linear | LETKF runner uses `option_mask=2`; the included result directory itself is named with `mask_1` | LETKF `r=3`, inflation `1.00`, `option_mask=1` |
| 2, all arctan | LETKF runner uses `option_mask=2`, in addition to the driver ignoring nonlinearity | LETKF `r=3`, inflation `1.00`, `option_mask=1` |
| 3, WDG/WSG/TPH | Both submitted masks select only WSG; they omit WDG and direct TG/TRG/PSG. EnSF also uses `r=2` in its filename/config convention | Mask includes WDG, WSG, TG, TRG, PSG; LETKF `r=2`, inflation `1.15`; EnSF inflation `1.00` |
| 4, pressure only | LETKF uses `option_mask=2`; the EnSF runner is labeled with `r=2` | LETKF `r=2`, inflation `1.30`, `option_mask=1`; EnSF inflation `1.00` |

Every submitted runner also leaves `code` blank. Cases with identical method,
radius, inflation, and mask therefore write to the same raw run directory; in
particular, cases 1 and 2 can overwrite or mix one another. The corrected
workflow assigns a distinct output root to every case.

Exact copies of the submitted CSVs are retained in
[`emmanuella_attempt/submitted_configs`](emmanuella_attempt/submitted_configs/).

## Remaining report/code ambiguity

Equation 16 in the defense report specifies standardized arctangent inputs,
but Jack's archived case-2 LETKF tuning config has
`normalize_nonlinear=False`. Its `r=3` summary reproduces the report's Table 7
values (for example UG1 `1.995447...`, VG1 `1.556011...`, TG1 `1.723083...`).

For that reason the canonical `case2_arctan/letkf.csv` follows the archived run
that generated the reported numbers. `case2_arctan/letkf_paper_spec.csv`
instead follows Equation 16 and writes to a separate directory. Comparing those
two runs is the appropriate way to resolve this last scientific discrepancy.
