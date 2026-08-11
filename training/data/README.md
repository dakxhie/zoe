# Training data directories

| Path | Purpose |
|------|---------|
| `raw/` | Ingested candidates / review queues (not training-ready) |
| `clean/` | Validated, privacy-filtered examples accepted for splitting |
| `train/` | SFT training split only |
| `validation/` | Early-stop / tuning split |
| `held_out_eval/` | **Never** mixed into training |
| `corrections/` | Failure → ideal records |
| `seeds/` | Curated format exemplars (high quality, small N) |

Seeds illustrate schema and personality balance; they are **not** a complete training set.

Do not dump `data/history` or telemetry here automatically—use `training.schema.ingest` and human review.
