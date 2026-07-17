# 🔎 DataSherlock

**AI-powered data quality and analytics assistant.** Upload a dataset, get instant profiling, validation, visual analytics, AI-generated insights, and natural-language SQL querying — all in one Streamlit app.

## Features

- **📁 Upload CSV/TSV** — drag and drop any dataset to get started
- **📊 Automated Profiling** — column-by-column breakdown: datatype, null %, unique values, duplicates
- **✅ Data Quality Validation** — rule-based checks for nulls, blank strings, duplicate rows, and constant columns
- **📈 Visual Analytics** — interactive Plotly charts for missing values and column datatype distribution
- **🤖 AI Insights (Gemini)** — a structured, plain-English summary of the dataset, prioritized data quality issues, and concrete recommendations, generated from the computed metadata (not raw data) to keep requests small and fast
- **💬 Ask Your Data** — type a question in plain English (e.g. *"What is the average fare by passenger class?"*); Gemini translates it into SQL, and DuckDB executes it instantly against your dataset in-memory

## Tech Stack

- **Frontend / App:** [Streamlit](https://streamlit.io)
- **Data:** Pandas
- **Visualization:** Plotly
- **AI:** Google Gemini API (`google-genai` SDK), model: `gemini-3.5-flash`
- **SQL Engine:** [DuckDB](https://duckdb.org) — in-memory, no external database needed
- **Config:** `python-dotenv` for local secrets management

## Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/NEERAJM07/Data_Sherlock.git
cd Data_Sherlock
```

### 2. Set up a virtual environment
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your Gemini API key
Get a free key from [Google AI Studio](https://aistudio.google.com/apikey), then create a `.env` file in the project root:
```
GEMINI_API_KEY=your_key_here
```
(This file is git-ignored and never committed — see `.gitignore`.)

### 5. Run the app
```bash
python -m streamlit run app.py
```

## Project Structure

```
Data_Sherlock/
├── app.py              # Streamlit UI and app flow
├── profiler.py          # Column-level profiling
├── validator.py          # Data quality rule checks
├── dashboard.py           # Summary metrics (rows, nulls, duplicates, quality score)
├── charts.py               # Plotly visualizations
├── ai_service.py             # Gemini-powered dataset insights
├── sql_engine.py               # Natural language → SQL via Gemini + DuckDB
├── sample_data/                  # Example datasets for testing
└── requirements.txt
```

## Safety Notes

`sql_engine.py` treats LLM-generated SQL as untrusted input: only `SELECT`/`WITH` statements are allowed through, and anything resembling `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, or similar mutating/administrative keywords is rejected before it ever reaches DuckDB.

## Roadmap

- [ ] Data dictionary generation
- [ ] Export reports (PDF / HTML / CSV)
- [ ] Snowflake integration for querying live warehouse tables

## Author

Built by **Neeraj M** — Data Engineer.
