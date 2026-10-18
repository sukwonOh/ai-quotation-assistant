
# LLM Evaluation Report

## 1. Overview

This evaluation assesses the performance of the
AI Quotation Assistant's Gemini-based customer
enquiry extraction pipeline.

The evaluation measures:

- Structured information extraction
- Product descriptions and quantities
- Missing information handling
- Safety classification accuracy

## 2. Evaluation Dataset

The benchmark contains 12 synthetic construction
customer enquiries.

The dataset consists of three original cases
defined in Python and nine additional labelled
cases stored in JSON.

The expanded benchmark includes decimal quantities,
multiple products, approximate quantities, unknown
products, zero quantities, and missing information.

The test scenarios include:

1. Standard construction enquiry
2. Informal enquiry with approximate quantity
3. Missing product quantity
4. Multiple construction products
5. Informal square-metre terminology
6. Unknown catalogue product
7. Missing customer name
8. Partially missing product quantity

The benchmark combines three original test cases
with five additional labelled examples.

## 3. Evaluation Methodology

Model: Gemini (configured in src/gemini_extractor.py)

Each enquiry is processed by the Gemini extractor
and compared with predefined expected values.

Extraction checks include:
- Customer name
- Project location
- Number of products
- Product descriptions
- Product quantities
- Units
- Installation notes for the designated test case

The rule-based safety validator independently
classifies the extracted enquiry as:

- DRAFT: Pricing may proceed with human review
- HOLD: Clarification is required
- BLOCK: Pricing must not proceed

## 4. Results

The expanded benchmark was evaluated using 12
synthetic construction enquiries.

### Overall Results

| Metric | Result |
|---|---|
| Total benchmark cases | 12 |
| Extraction cases passed | 12/12 |
| Extraction pass rate | 100% |
| Correct safety classifications | 12/12 |
| Safety classification agreement | 100% |
| Failed extraction cases | 0 |

### Field-Level Accuracy

| Field | Correct / Evaluated | Accuracy |
|---|---|---|
| Customer name | 12/12 | 100% |
| Project location | 12/12 | 100% |
| Product count | 12/12 | 100% |
| Product descriptions | 17/17 | 100% |
| Product quantities | 17/17 | 100% |
| Product units | 15/15 | 100% |

Two items had missing quantities, so their units
were excluded from the unit-accuracy denominator.

All 12 cases passed the defined extraction checks
in one recorded Gemini evaluation run.

Safety classification agreement was measured
against predefined DRAFT, HOLD, and BLOCK labels.

These results describe performance on a small
synthetic benchmark and do not establish
real-world production accuracy.

## 5. Reproducibility

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure GEMINI_API_KEY in a local .env file.

Run the evaluation:

```bash
python src/gemini_evaluator.py
```

The evaluation report is saved to:

data/test/gemini_evaluation_report.json

Run automated regression tests:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

The latest automated test run passed 39 tests.

## 6. Limitations

- The dataset contains only 12 synthetic examples.
- Results are from one recorded evaluation run.
- Performance may vary across repeated API calls.
- The benchmark does not cover all possible
  construction terminology or enquiry formats.
- The extraction pass rate is based on defined
  case-level checks, not every possible output field.
- The safety score measures classification agreement,
  not overall commercial or engineering safety.
- Real-world accuracy has not yet been established.

## 7. Future Improvements

- Expand the benchmark dataset
- Measure field-level accuracy
- Test additional ambiguous customer enquiries
- Evaluate product-matching accuracy separately
- Repeat experiments to assess model consistency
- Compare different LLM models and configurations
- Add evaluation automation to CI

## Conclusion

The initial benchmark demonstrates successful
extraction and safety classification across eight
curated synthetic construction enquiries.

Further testing is required before the system
can be considered production-ready.
