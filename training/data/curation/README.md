# Sprint 23 curation banks

Source-of-truth Python banks for curated SFT / corrections / held-out rows.

```bash
python -m training.data.curation.export_sprint23
```

Exports JSONL under `training/data/clean`, `held_out_eval`, and `corrections`.  
Does **not** train, download weights, or change Zoe runtime.
