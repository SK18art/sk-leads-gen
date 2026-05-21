📊 Company Lead Matcher

A fullstack web application that matches companies with potential leads using either:

🤖 OpenAI (AI-based scoring)
📏 Rule-based logic (fallback system)

The app evaluates how well a lead fits a company and produces a match score, verdict, reasons, and recommended action.

🚀 Features
Add and manage companies
Add and manage leads
Automatically match all companies with all leads
AI-powered evaluation using OpenAI (optional)
Rule-based fallback matching (always works)
Match scoring from 0 to 100
Verdict classification:
good_match
possible_match
bad_match
Ranked match history
Search & filter results
SQLite database storage
🧠 How Matching Works

Each company-lead pair is evaluated based on:

If OpenAI is enabled:
AI analyzes:
Industry fit
Location match
Age / life stage relevance
Income suitability
Business relevance
Returns structured result:
Score (0–100)
Verdict
Confidence
Reasons
Recommended action
If OpenAI is disabled:

The system uses rule-based scoring:

Location similarity
Industry logic (healthcare, logistics, food, furniture, etc.)
Age & working status
Income level
Family situation
🏗️ Tech Stack

Frontend

HTML
CSS
JavaScript (Vanilla)

Backend

Python
Flask

Database

SQLite

AI (optional)

OpenAI API
📁 Project Structure
sk-leads-gen/
│
├── app.py                  # Flask backend (main logic)
├── requirements.txt        # Dependencies
├── .env                    # Environment variables
├── lead_matcher.db        # SQLite database
│
├── templates/
│   └── index.html          # Frontend UI
│
├── static/
│   ├── css/
│   │   └── styles.css      # Styling
│   └── js/
│       └── app.js          # Frontend logic
⚙️ Installation & Setup
1. Clone project
git clone <your-repo-url>
cd sk-leads-gen
2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
3. Install dependencies
pip install -r requirements.txt
4. Configure environment variables

Create a .env file:

OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
USE_OPENAI=true
DATABASE_PATH=lead_matcher.db
5. Run the app
python app.py
6. Open in browser
http://127.0.0.1:5000
🔌 API Endpoints
Companies
GET /api/companies → List companies
POST /api/companies → Add company
Leads
GET /api/leads → List leads
POST /api/leads → Add lead
Matches
GET /api/matches → Get match history
POST /api/match/run → Run matching engine
DELETE /api/matches → Clear match history
System
GET /api/status → System status (DB + AI mode)
🧪 Example Workflow
Add a company
Add leads
Click Run Match
System compares all combinations
Results are stored and ranked
View best matches at the top
📊 Output Example
{
  "company_name": "MediCare Plus",
  "lead_name": "Anna",
  "match_score": 82,
  "verdict": "good_match",
  "confidence": "high",
  "reasons": [
    "Lead is in target age group",
    "Healthcare service fits needs"
  ],
  "recommended_action": "Prioritize outreach"
}
🔄 Architecture Overview
Frontend (HTML/JS)
        ↓
Flask API (app.py)
        ↓
SQLite Database
        ↓
Matching Engine
   ├── OpenAI (optional)
   └── Rule-based fallback
🧩 Key Idea

This project demonstrates how to combine:

Web development (Flask)
Data storage (SQLite)
Business logic (matching engine)
AI integration (OpenAI fallback system)
🛠️ Future Improvements
Authentication system
Better filtering & segmentation
Pagination for large datasets
Dashboard with charts
Export results to CSV/Excel
Advanced AI prompt tuning
👨‍💻 Author

Built as a fullstack learning project for understanding:

APIs
Databases
Frontend-backend communication
AI integration
Business logic design