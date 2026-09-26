# Channel learning samples

Build with:

```text
python -m GP_AI build-channel-samples --max-ides 30 --scan-stride 5
python -m GP_AI build-channel-samples --industry 食品饮料 --max-ides 200
```

Outputs:

- `channel_samples.parquet` (or `.csv` fallback)
- `channel_samples_meta.json`

Labels:

- `y_alpha`: stock−HY1 excess > 5%, peak MDD < 8%, no lower-rail break
- `y_sector`: HY1−market(`sh000001`) excess > 0

`as_of` = ascending-channel **entered** event day.
