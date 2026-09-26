# GP_AI model artifacts

Train models with:

```text
python -m GP_AI train-ranker
python -m GP_AI train-signal
python -m GP_AI train-anomaly
```

Expected files after training:

- `ranker.joblib`
- `signal_lgb.joblib`
- `signal_xgb.joblib` (optional contrast model)
- `anomaly.joblib`
- `meta.json`
