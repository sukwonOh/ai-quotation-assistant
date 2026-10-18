# AI Quotation Assistant

**An AI-assisted construction quotation prototype that transforms customer enquiries into structured, reviewable quotations.**

Built with **Python, Google Gemini, Pydantic, pandas, Streamlit, and ReportLab**. The language model extracts information from unstructured text, while catalogue matching, price calculation, and safety checks run in Python. A reviewer must approve a draft before JSON and PDF export are available.

> **Project status:** Portfolio MVP / demonstration. Uses a synthetic product catalogue. Not intended for unattended production quoting or customer delivery without further validation.


## Live Demo

The AI Quotation Assistant is deployed on Streamlit
Community Cloud.

**[Open the Streamlit Demo](https://ai-quotation-assistant-r7zf84qw8sdbpw47t3fqwh.streamlit.app/)**

The demonstration currently has restricted access.
Invited viewers must sign in and enter the demo password.

### Demo Capabilities

- Extract structured customer enquiries using Google Gemini
- Validate product quantities and safety conditions
- Match products with a synthetic construction catalogue
- Generate deterministic quotations with Australian GST
- Review and approve quotations before export
- Download approved quotations as JSON or PDF

**Note:** This application is a portfolio prototype.
Prices are synthetic and should not be used for real
construction quotations.

## Features

- **LLM-based extraction:** Extract customer details, project information, product descriptions, quantities, units, and notes from an enquiry using Google Gemini and a Pydantic schema.
- **Catalogue matching:** Match extracted product names to items in a CSV catalogue (case-insensitive exact matching).
- **Deterministic pricing:** Calculate material quantity including waste, material cost, labour cost, GST, and quotation totals using catalogue values rather than LLM-generated prices.
- **Safety checks:** Block missing or invalid quantities, unknown products, and unsupported units; hold enquiries with approximate quantities; flag installation scope for review.
- **Human approval:** Require a named reviewer and explicit confirmation before approved export.
- **Exports:** Download approved quotations as JSON or PDF, including review details and approval timestamp.
- **Automated tests:** A `unittest` suite covering pricing, safety validation, pipeline blocking, PDF export, and Gemini evaluation (43 tests passing as of 18 October 2026).

## Workflow

```text
Customer enquiry (free text)
            |
            v
Google Gemini -> structured enquiry (Pydantic)
            |
            v
Safety checks -> BLOCK / HOLD / DRAFT
            |
       DRAFT only
            v
Catalogue matching + unit validation
            |
            v
Deterministic calculation (materials + waste + labour + GST)
            |
            v
Streamlit review -> APPROVE / REJECT
            |
       APPROVED only
            v
JSON / PDF download
```

**Important:** `DRAFT` means the enquiry has passed the implemented pre-pricing checks; it does **not** mean the resulting quote is automatically safe, accurate, or ready to send. Human review remains necessary. Installation-related warnings are displayed but do not, by themselves, change `DRAFT` to `HOLD`.

## Example

**Input enquiry:**

> Hi, my name is Alex from Example Construction. We need 120 m2 of Standard Aluminium Cladding and 120 m2 of 50mm Insulation Board for a commercial property in Parramatta, Sydney. Please provide a quotation.

**Illustrative result using the synthetic catalogue:**

| Product | Quantity | Total (AUD, incl. GST) |
| --- | ---: | ---: |
| Standard Aluminium Cladding | 120 m2 | $18,282.00 |
| 50mm Insulation Board | 120 m2 | $4,633.20 |
| **Quotation total** | | **$22,915.20** |

The example includes **$20,832.00 subtotal** and **$2,083.20 GST**. These prices are sample values, not market quotations.

## Technology stack

| Technology | Purpose |
| --- | --- |
| Python | Application logic, validation, and pricing |
| Google Gemini (`google-genai`) | Extract structured information from customer enquiries |
| Pydantic | Validate the LLM response structure |
| pandas / CSV | Load and match product catalogue entries |
| Streamlit | Interactive user interface and approval workflow |
| ReportLab | Generate approved quotation PDFs |
| `unittest` | Automated regression tests |

## Model Evaluation

The Gemini extraction pipeline was evaluated using
12 synthetic construction customer enquiries.

The benchmark covers multiple products, approximate
quantities, missing information, unknown products,
decimal quantities, and zero quantities.

### Evaluation Results

| Metric | Result |
|---|---|
| Extraction pass rate | 100% (12/12) |
| Safety classification agreement | 100% (12/12) |
| Customer name accuracy | 100% (12/12) |
| Project location accuracy | 100% (12/12) |
| Product count accuracy | 100% (12/12) |
| Product description accuracy | 100% (17/17) |
| Quantity accuracy | 100% (17/17) |
| Unit accuracy | 100% (15/15) |
| Automated regression tests | 43 passed |

### Consistency Evaluation

Three construction enquiries were evaluated three times
each, producing nine Gemini extraction attempts.

| Scenario | Extraction | Safety | Pairwise agreement |
|---|---|---|---|
| Standard enquiry | 3/3 | 3/3 | 100% |
| Approximate quantity | 3/3 | 3/3 | 100% |
| Missing quantity | 3/3 | 3/3 | 100% |

The consistency evaluation compares customer names,
project locations, product descriptions, quantities,
and units across repeated extractions.

### Robustness Evaluation

Five challenging synthetic enquiries were tested.

| Scenario | Extraction | Safety |
|---|---|---|
| Corrected measurement | PASS | PASS |
| Thickness versus area | PASS | PASS |
| Prompt injection | PASS | PASS |
| Missing area | PASS | PASS |
| Approximate quantity | PASS | PASS |

All five enquiries passed the defined extraction
and safety checks in the recorded evaluation run.

These experiments use small synthetic datasets.
They do not establish general reliability,
prompt-injection resistance, or production readiness.

These results represent one evaluation run on a
small, curated synthetic dataset. They do not
establish real-world production accuracy.

For methodology, detailed results, and limitations,
see the full report:

[View LLM Evaluation Report](docs/evaluation.md)

## Project structure

Key project files and directories:

```text
ai-quotation-assistant/
│
├── app/
│   └── app.py                     # Streamlit application
│
├── data/
│   ├── evaluation/
│   │   ├── benchmark_cases.json
│   │   └── robustness_cases.json
│   ├── raw/
│   ├── synthetic/
│   │   └── product_catalogue.csv
│   └── test/
│
├── src/
│   ├── catalogue.py               # Product catalogue
│   ├── enquiry_matcher.py         # Product matching
│   ├── gemini_extractor.py         # Gemini structured extraction
│   ├── quotation_service.py       # Quotation workflow
│   ├── quotation_module.py        # Pricing calculations
│   ├── quotation_safety.py        # Safety rules
│   ├── pdf_exporter.py            # PDF generation
│   ├── gemini_evaluator.py        # LLM field-level evaluation
│   ├── consistency_evaluator.py   # Repeated-run comparison
│   ├── run_consistency_evaluation.py
│   └── run_robustness_evaluation.py
│
├── tests/                          # Automated unit tests
│
├── docs/
│   ├── evaluation.md              # Evaluation report
│   └── screenshots/               # Application screenshots
│
├── .github/
│   └── workflows/
│       └── tests.yml              # GitHub Actions CI
│
├── .env.example                    # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

Earlier prototype modules are also retained in the src/
directory.

## Run locally

**Prerequisites:** Python 3.13 (development environment used for this project), a Gemini API key, and internet access for LLM extraction.

1. Clone the repository and enter the project folder:

   ```bash
   git clone https://github.com/sukwonOh/ai-quotation-assistant.git
   cd ai-quotation-assistant
   ```

2. Create and activate a virtual environment (Windows CMD):

   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Configure environment variables:

   Copy the example environment file (Windows CMD):

   ```cmd
   copy .env.example .env
   ```

   Open the newly created `.env` file and set:

   ```dotenv
   GEMINI_API_KEY=your_actual_api_key
   DEMO_PASSWORD=your_private_demo_password
   ```

   Replace the placeholder values with your own credentials.

   Never commit `.env` to GitHub. The file is excluded
   by `.gitignore`.

5. Start the application:

   ```bash
   python -m streamlit run app/app.py
   ```

6. In the web interface, submit an enquiry, inspect extraction and safety results, generate a draft if permitted, review the prices, and approve before downloading the quotation.

## Run automated tests

From the project root, with the environment activated:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

The suite currently covers PDF export constraints, pipeline safety, calculation validation, and quotation safety rules. The latest locally verified test run passed **43 tests**.

## Safety, limitations, and next steps

- The Gemini model is used for **information extraction**, not for inventing prices or calculating GST.
- Product matching currently relies on **case-insensitive exact name matching**, rather than semantic retrieval. Unmatched items are not automatically priced by the Streamlit workflow.
- Safety checks are rule-based and not a replacement for professional assessment of measurements, scope, site conditions, or contractual terms.
- Approval is implemented in the Streamlit session; this is **not yet** a persistent, authenticated, auditable multi-user workflow.
- No email inbox ingestion, accounting-system integration, or automated sending is currently implemented in this portfolio app.
- Planned improvements include broader test coverage, a reproducible LLM evaluation set, CI, deployment safeguards, and application screenshots.

## Application Screenshots

### AI Enquiry Extraction
![AI Extraction](docs/screenshots/ai-extraction.png)

### Product Matching & Quotation Calculation
![Quotation Workflow](docs/screenshots/quotation-workflow.png)

### Human Review & Approval
![Human Approval](docs/screenshots/human-approval.png)

## Author

Created by [sukwonOh](https://github.com/sukwonOh) as an applied AI / NLP portfolio project.
