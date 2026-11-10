# Data Analyst Work Package — DocuSense AI

## Task 5.1 — Benchmark dataset
Created a 30-pair benchmark with 60 source statements. The test set includes direct policy conflicts, scope variations, historical policy updates, dependency/environment conflicts, equivalent claims, and neutral comparisons. Each row contains a gold label and rationale. This supports repeatable evaluation and regression testing.

## Task 5.2 — Analytical verification
The `evaluate.py` script uses NumPy for confusion-matrix and metric calculations, Pandas for dataset joins, and Matplotlib for charts. It reports multi-class accuracy and macro metrics, actionable contradiction precision/recall/F1, false-positive rate, a clearly defined project-specific consistency indicator, and mean/median/p95 processing latency. Extraction precision/recall are supported when statement-level extraction predictions are supplied.

## Task 5.3 — Visual analytics
The script generates:
1. Confusion matrix.
2. Benchmark category breakdown.
3. Evaluation metric comparison.
4. Processing latency histogram when timings are available.

## Interpretation and client-reporting safeguards
The charts in `demo_output/` are generated from deliberately synthetic predictions solely to demonstrate the reporting pipeline. They are not real DocuSense performance results. For the final client report, run the script against actual system predictions and measured latency. State benchmark size, label definitions, test date, model/version, and whether results are human-adjudicated. Do not present the consistency indicator as a universal or externally validated score.
