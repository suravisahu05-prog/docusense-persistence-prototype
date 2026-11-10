# DocuSense AI — Data Analyst Evaluation Pack

## Contents
- `benchmark_pairs.csv`: 30 labeled statement pairs covering contradiction, scope, time, dependencies, entailment and neutral cases.
- `extraction_ground_truth.csv`: 60 statement-level extraction targets.
- `system_results_template.csv`: template for your system's predictions and latency.
- `evaluate.py`: NumPy/Pandas/Matplotlib evaluation script.
- `demo_system_results.csv`: explicitly synthetic example predictions, only to verify the charts and script.
- `demo_output/`: example charts generated from the synthetic demo predictions.

## Run the evaluation
Install dependencies:
```bash
python -m pip install numpy pandas matplotlib
```
Copy `system_results_template.csv` to `system_results.csv`, then fill one row per `case_id` with your DocuSense output:
- `predicted_label`: one of CONTRADICTION, SCOPE_DIFFERENCE, TEMPORAL_CHANGE, DEPENDENCY_CONFLICT, ENTAILED, NEUTRAL, NEEDS_REVIEW
- `confidence`: model confidence estimate from 0 to 1
- `processing_ms`: measured end-to-end pair processing latency in milliseconds
- `extracted_statement_ids`: extracted statement identifiers, e.g. B001A;B001B
- `evidence_valid`: TRUE only if the cited quotation and source location are verifiably present

Then run:
```bash
python evaluate.py --benchmark benchmark_pairs.csv --predictions system_results.csv --out results
```

For extraction metrics, copy `extraction_results_template.csv` to `extraction_results.csv` and add one row per expected statement (60 rows for this benchmark). Use `expected_extracted` from `extraction_ground_truth.csv` and set `extracted` to TRUE only when your system actually extracted that statement. Then run:
```bash
python evaluate.py --predictions system_results.csv --extraction extraction_results.csv --out results
```

## Metric definitions
- Classification accuracy = correct labels / all benchmark pairs.
- Macro precision/recall/F1 = unweighted average across the seven labels.
- Contradiction precision = TP/(TP+FP), where actionable conflicts include CONTRADICTION and DEPENDENCY_CONFLICT.
- False-positive rate = FP/(FP+TN), where non-conflict gold classes are negative.
- Consistency indicator = 100 × (1 − false-positive rate). This is a project-specific dashboard indicator, not a validated universal consistency score.
- Latency = mean, median and p95 of recorded `processing_ms`.
- Extraction precision/recall are calculated only when statement-level extraction outputs are supplied. The provided extraction ground truth is a target set, not evidence that the system extracted it correctly.

## Important
The included `demo_system_results.csv` is synthetic and deliberately contains some errors to demonstrate the evaluation pipeline. Do not report its scores as actual product performance. Replace it with outputs from the real DocuSense build before presenting measured accuracy to a client. Human review remains necessary.
