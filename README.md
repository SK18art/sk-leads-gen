# Company Lead Matcher Full-Stack App

This is a small full-stack app that turns the original company-lead matching script into a persistent web application.

It includes:

- Python Flask backend
- SQLite3 persistent storage
- Plain HTML, CSS, and JavaScript frontend
- Optional OpenAI structured matching
- Local rule-based fallback matching when no OpenAI API key is available

## Project structure

```text
company_lead_matcher_app/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── styles.css
    └── js/
        └── app.js
```

When the app starts, it creates this SQLite database automatically:

```text
lead_matcher.db
```

The database contains three tables:

- `companies`
- `leads`
- `matches`

The app also seeds your original mock companies and leads if the database is empty.

## How to run

### 1. Open a terminal in the project folder

```bash
cd company_lead_matcher_app
```

### 2. Create a virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Optional: configure OpenAI

The app works without OpenAI by using local deterministic rules.

To use OpenAI matching, copy `.env.example` to `.env`:

macOS/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
copy .env.example .env
```

Then edit `.env`:

```text
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
USE_OPENAI=true
DATABASE_PATH=lead_matcher.db
```

To force local rule-based scoring only:

```text
USE_OPENAI=false
```

### 5. Start the app

```bash
python app.py
```

### 6. Open the browser

Go to:

```text
http://127.0.0.1:5000
```

## How to use the app

1. Add new companies from the **Add Company** form.
2. Add new leads from the **Add Lead** form.
3. In **Run Matching**, choose:
   - all companies and all leads, or
   - one company, or
   - one lead, or
   - one specific company-lead pair.
4. Click **Run Match**.
5. Review the ranked results in **Ranked Matches**.
6. Results are saved permanently in SQLite until you click **Clear Match History**.

## API endpoints

### Companies

```http
GET /api/companies
POST /api/companies
```

### Leads

```http
GET /api/leads
POST /api/leads
```

### Matches

```http
GET /api/matches
POST /api/match/run
DELETE /api/matches
```

### Status

```http
GET /api/status
```

## Notes

- If `OPENAI_API_KEY` is missing, the backend automatically uses local rule-based scoring.
- If OpenAI fails during a request, the backend falls back to local rule-based scoring.
- Match results are append-only. Running matching multiple times will create new saved results.
- `lead_matcher.db` is your persistent database file. Do not delete it unless you want to reset stored data.
