# FOMC Decision Validation Tool

A Streamlit application for validating LLM-extracted policy decisions from Federal Reserve FOMC meeting transcripts.

## Live App

🌐 **[Access the app on Streamlit Cloud](https://your-app-url.streamlit.app)** *(update this URL after deployment)*

## Purpose

This tool supports an academic research project validating whether Claude correctly identified what decisions the FOMC made at each meeting and whether it scored those decisions' policy stance correctly.

**Workflow:**
1. Claude (batch API) processed ~300 FOMC transcripts (1976-2019) and extracted decisions
2. Human coders use this tool to validate a sample of those extractions
3. We compute precision, recall, and score correlations to assess Claude's accuracy

## Setup (Local Development)

### Prerequisites

- Python 3.9+
- pip

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/fomc-decision-validation.git
   cd fomc-decision-validation
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Data files should already be in place:
   ```
   data/
   ├── decisions/
   │   ├── adopted_decisions_19791006.csv
   │   ├── adopted_decisions_19940816.csv
   │   ├── adopted_decisions_20081216.csv
   │   ├── adopted_decisions_20110809.csv
   │   └── adopted_decisions_20190731.csv
   ├── transcripts.parquet
   ├── alternatives.pkl
   └── coding_results/
   ```

### Running Locally

```bash
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`.

## Usage

### 1. Enter Your Coder ID

In the sidebar, enter your unique identifier (e.g., your initials). This is saved with all your coding results.

### 2. Select a Meeting

Choose from one of the 5 target meetings:
- **October 6, 1979** - Volcker's "Saturday Night Special"
- **August 16, 1994** - Greenspan tightening cycle
- **December 16, 2008** - Financial crisis, zero lower bound
- **August 9, 2011** - Extended period debate
- **July 31, 2019** - Powell mid-cycle cut

### 3. Review Reference Materials

- **Policy Alternatives**: Expand to see the A/B/C policy options staff prepared
- **Full Transcript**: Expand to read or search the meeting transcript

### 4. Validate Each Decision

For each decision Claude identified:

1. **Occurrence**: Did this decision actually happen at this meeting?
2. **Type**: Is the classification (rate decision/communication/other) correct?
3. **Score**: Rate the policy stance from -3 (strongly dovish) to +3 (strongly hawkish)
4. **Evidence**: Note where in the transcript this decision is documented
5. **Notes**: Add any concerns or ambiguities
6. **Confidence**: How confident are you in your validation?

Click "Mark Complete" when done with each decision.

### 5. Check for Missing Decisions

After validating all decisions, indicate whether Claude missed any significant decisions.

### 6. Submit

Provide an overall assessment and submit. Results are saved to `data/coding_results/`.

## Output Format

Results are saved in two formats:

### JSON (detailed)
```json
{
  "metadata": {
    "meeting_date": "20081216",
    "coder_id": "BH",
    "coding_timestamp": "2025-01-15T14:32:00",
    ...
  },
  "decision_validations": [...],
  "missing_decisions": [...],
  "meeting_summary": {...}
}
```

### CSV (flattened)
One row per decision with all fields flattened for analysis.

## Score Scale Reference

| Score | Meaning |
|-------|---------|
| -3 | Strongly dovish (maximum accommodation) |
| -2 | Moderately dovish |
| -1 | Slightly dovish |
| 0 | Neutral |
| +1 | Slightly hawkish |
| +2 | Moderately hawkish |
| +3 | Strongly hawkish (maximum tightening) |

## Target Meetings

| Date | Era | Context | Alternatives? |
|------|-----|---------|---------------|
| 19791006 | Volcker | "Saturday Night Special" - major policy shift | No |
| 19940816 | Greenspan | Mid-cycle tightening | Yes |
| 20081216 | Bernanke | Financial crisis, zero lower bound | Yes |
| 20110809 | Bernanke | Post-crisis, "extended period" debate | Yes |
| 20190731 | Powell | Mid-cycle cut | Yes |

## Project Structure

```
fomc-decision-validation/
├── app.py                    # Main Streamlit application
├── config.py                 # Configuration settings
├── requirements.txt          # Dependencies
├── README.md                 # This file
├── .gitignore               # Git ignore rules
├── .streamlit/
│   └── config.toml          # Streamlit configuration
├── data/
│   ├── decisions/           # Claude's extracted decisions (CSVs)
│   ├── transcripts.parquet  # All transcripts (Parquet format)
│   ├── alternatives.pkl     # Policy alternatives
│   └── coding_results/      # Human coding output
└── utils/
    ├── __init__.py
    ├── data_loader.py       # Data loading functions
    └── export.py            # Export functions
```

## Deployment to Streamlit Community Cloud

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: FOMC Decision Validation Tool"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/fomc-decision-validation.git
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository: `YOUR_USERNAME/fomc-decision-validation`
5. Set the main file path to: `app.py`
6. Click "Deploy"

The app will be available at `https://your-app-name.streamlit.app`

### Important Notes for Deployment

- **Data files are included** in the repository (~52 MB total)
- **Coding results** are saved locally on each user's session (not persisted on cloud)
- For persistent storage of coding results, consider integrating with Google Sheets or a database

## Troubleshooting

### "No module named 'pyarrow'"
```bash
pip install pyarrow
```

### Transcript not loading
Ensure `data/transcripts.parquet` exists and is a valid Parquet file.

### Progress not saving
- Locally: Check that `data/coding_results/` directory exists and is writable
- On Streamlit Cloud: Results are session-only; download before closing the browser

## License

This project is part of academic research. Contact the authors for usage permissions.
