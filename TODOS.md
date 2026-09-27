# TODOS

## Validate redflags against a known real event

**What:** Manually search news/fiscalização reports for a public event matching one of the existing 751 distribuidora or 13 UF z-score redflags (e.g. BA 2020-12, ENEL CE 2026-04, COPEL-DIS 2025-06).

**Why:** `docs/crisp_dm.md` Phase 5 (Avaliação) has flagged this as the last unclosed gap in the Fase A success criteria — without it, the redflags are unvalidated signal, not a corroborated finding.

**Pros:** Turns a heuristic into a citable finding if even one hit lands; closes the CRISP-DM Phase 5 gap formally.

**Cons:** Manual search with no guarantee of a match; time cost competes directly with the model+SHAP+PDF work already prioritized.

**Context:** Deferred during the 2026-09-09/10 `/plan-ceo-review` session (decision D9) specifically because near-term time is already claimed by `src/model_redflags.py` (feature engineering, target-encoding shrinkage, calendar reindexing, SHAP). Start from the top-5 highest-|z| redflags already in `data/analise/redflags_dist.csv` and `data/analise/redflags_uf.csv`.

**Effort:** S (human ~1-2h) → with CC: S.

**Priority:** P2.

**Depends on / blocked by:** Nothing — can run independently of `model_redflags.py` using the existing z-score outputs.
