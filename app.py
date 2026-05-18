import itertools
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Literal, Optional

from flask import Flask, jsonify, render_template, request
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "lead_matcher.db"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
USE_OPENAI = os.getenv("USE_OPENAI", "true").lower() in {"1", "true", "yes"}

app = Flask(__name__)


class MatchAssessment(BaseModel):
    company_name: str
    lead_name: str
    match_score: int = Field(description="Score from 0 to 100", ge=0, le=100)
    verdict: Literal["good_match", "possible_match", "bad_match"]
    confidence: Literal["low", "medium", "high"]
    reasons: list[str] = Field(description="Short reasons for the assessment")
    recommended_action: str = Field(description="Suggested next step")


SYSTEM_PROMPT = """
You are a lead-company matching evaluator.

Your task is to assess whether a lead is a good potential customer for a company.

Evaluate the match using:
1. Location fit
2. Industry/product relevance
3. Likely customer need
4. Income/affordability fit
5. Life-stage and family context
6. Overall commercial potential

Important rules:
- Do not make assumptions that are not supported by the data.
- Do not over-rely on only one field.
- If the match is uncertain, use "possible_match".
- Keep the reasons short and practical.
- Use this scoring logic:
  - 0-39: bad_match
  - 40-69: possible_match
  - 70-100: good_match
""".strip()

SEED_COMPANIES = [
    ("Shima Company", "shima_company@gmail.com", "Clothing", "Berlin, Germany", "Clothing company for elderly people with 10 stores across Berlin."),
    ("GreenFork Foods", "greenfork_foods@gmail.com", "Food & Beverage", "Hamburg, Germany", "Sustainable meal-prep company offering plant-based lunches to offices and universities."),
    ("UrbanMove Logistics", "urbanmove_logistics@gmail.com", "Urban Logistics", "Munich, Germany", "Last-mile delivery company using cargo bikes and electric vans for local retailers."),
    ("BrightNest Interiors", "brightnest_interiors@gmail.com", "Home & Furniture", "Cologne, Germany", "Interior design and furniture retailer focused on compact apartments and student housing."),
    ("MediCare Plus", "medicare_plus@gmail.com", "Healthcare", "Frankfurt, Germany", "Private healthcare provider offering home-care services and medical equipment for seniors."),
]

SEED_LEADS = [
    ("George", "george@gmail.com", 54, "Male", "Self-employed", "Germany", "Berlin", "Married, 2 kids", "Medium"),
    ("Anna", "anna.schmidt@gmail.com", 72, "Female", "Retired", "Germany", "Berlin", "Widowed, 1 kid", "Medium"),
    ("Lukas", "lukas.weber@gmail.com", 29, "Male", "Employed", "Germany", "Munich", "Single", "High"),
    ("Miriam", "miriam.klein@gmail.com", 41, "Female", "Employed", "Germany", "Hamburg", "Married, 1 kid", "Medium"),
    ("Tobias", "tobias.fischer@gmail.com", 22, "Male", "Student", "Germany", "Cologne", "Single", "Low"),
    ("Elena", "elena.meyer@gmail.com", 67, "Female", "Retired", "Germany", "Frankfurt", "Married, 3 kids", "Medium"),
    ("Daniel", "daniel.hoffmann@gmail.com", 36, "Male", "Employed", "Germany", "Berlin", "Married, no kids", "High"),
    ("Sofia", "sofia.wagner@gmail.com", 31, "Female", "Freelancer", "Germany", "Hamburg", "Single", "Medium"),
    ("Peter", "peter.becker@gmail.com", 58, "Male", "Self-employed", "Germany", "Munich", "Married, 2 kids", "High"),
    ("Clara", "clara.bauer@gmail.com", 45, "Female", "Unemployed", "Germany", "Cologne", "Divorced, 1 kid", "Low"),
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            industry TEXT,
            location TEXT,
            description TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            age INTEGER,
            gender TEXT,
            working_status TEXT,
            country TEXT,
            city TEXT,
            family TEXT,
            income_status TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            lead_id INTEGER NOT NULL,
            company_name TEXT NOT NULL,
            lead_name TEXT NOT NULL,
            match_score INTEGER,
            verdict TEXT NOT NULL,
            confidence TEXT NOT NULL,
            reasons TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(company_id) REFERENCES companies(id),
            FOREIGN KEY(lead_id) REFERENCES leads(id)
        );
        """
    )

    company_count = cur.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    if company_count == 0:
        cur.executemany(
            "INSERT INTO companies (name, email, industry, location, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            [(*row, now_iso()) for row in SEED_COMPANIES],
        )

    lead_count = cur.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    if lead_count == 0:
        cur.executemany(
            """
            INSERT INTO leads (name, email, age, gender, working_status, country, city, family, income_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [(*row, now_iso()) for row in SEED_LEADS],
        )

    conn.commit()
    conn.close()


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def get_company(company_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_lead(lead_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def build_prompt(company: dict, lead: dict) -> str:
    return f"""
Assess the following company-lead match.

Company:
Name: {company['name']}
Email: {company.get('email') or ''}
Industry: {company.get('industry') or ''}
Location: {company.get('location') or ''}
Description: {company.get('description') or ''}

Lead:
Name: {lead['name']}
Email: {lead.get('email') or ''}
Age: {lead.get('age') or ''}
Gender: {lead.get('gender') or ''}
Working Status: {lead.get('working_status') or ''}
Country: {lead.get('country') or ''}
City: {lead.get('city') or ''}
Family: {lead.get('family') or ''}
Income Status: {lead.get('income_status') or ''}

Return a structured assessment.
""".strip()


def verdict_from_score(score: int) -> str:
    if score >= 70:
        return "good_match"
    if score >= 40:
        return "possible_match"
    return "bad_match"


def local_rule_based_assessment(company: dict, lead: dict) -> dict:
    """Deterministic fallback so the app still works without an OpenAI API key."""
    score = 0
    reasons = []

    company_location = (company.get("location") or "").lower()
    lead_city = (lead.get("city") or "").lower()
    industry = (company.get("industry") or "").lower()
    description = (company.get("description") or "").lower()
    age = int(lead.get("age") or 0)
    working = (lead.get("working_status") or "").lower()
    income = (lead.get("income_status") or "").lower()
    family = (lead.get("family") or "").lower()

    if lead_city and lead_city in company_location:
        score += 25
        reasons.append("Lead is in the same city as the company.")
    elif lead.get("country", "").lower() == "germany":
        score += 10
        reasons.append("Lead is in the same country.")

    if "elderly" in description or "senior" in description or "seniors" in description:
        if age >= 65 or "retired" in working:
            score += 35
            reasons.append("Lead fits the senior customer profile.")
        elif age >= 50:
            score += 20
            reasons.append("Lead is close to the older-customer profile.")

    if "meal-prep" in description or "food" in industry:
        if "employed" in working or "student" in working or "freelancer" in working:
            score += 25
            reasons.append("Working/student profile may fit convenient meals.")

    if "logistics" in industry:
        if "self-employed" in working or "retailer" in description or income == "high":
            score += 20
            reasons.append("Commercial or high-income profile may fit delivery services.")

    if "furniture" in industry or "interior" in description:
        if "student" in working or "single" in family or income in {"medium", "high"}:
            score += 25
            reasons.append("Life stage may fit compact apartment or furniture needs.")

    if "healthcare" in industry or "medical" in description or "home-care" in description:
        if age >= 60 or "retired" in working:
            score += 35
            reasons.append("Lead is likely relevant for senior healthcare services.")

    if income == "high":
        score += 10
        reasons.append("High income improves affordability.")
    elif income == "medium":
        score += 7
        reasons.append("Medium income gives reasonable affordability.")
    elif income == "low":
        score += 2
        reasons.append("Low income may limit affordability.")

    score = max(0, min(score, 100))
    verdict = verdict_from_score(score)
    confidence = "high" if score >= 75 or score <= 25 else "medium"
    if not reasons:
        reasons = ["There is limited evidence of strong fit in the available data."]

    action = "Prioritize outreach." if verdict == "good_match" else "Nurture and collect more data." if verdict == "possible_match" else "Do not prioritize now."

    return {
        "company_name": company["name"],
        "lead_name": lead["name"],
        "match_score": score,
        "verdict": verdict,
        "confidence": confidence,
        "reasons": reasons[:4],
        "recommended_action": action,
    }


def assess_with_openai(company: dict, lead: dict) -> Optional[dict]:
    if not USE_OPENAI or OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = build_prompt(company, lead)

    for attempt in range(3):
        try:
            response = client.responses.parse(
                model=MODEL,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                text_format=MatchAssessment,
                temperature=0,
            )
            return response.output_parsed.model_dump()
        except TypeError:
            # Some models/SDK versions may not accept temperature with structured parsing.
            response = client.responses.parse(
                model=MODEL,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                text_format=MatchAssessment,
            )
            return response.output_parsed.model_dump()
        except Exception:
            if attempt == 2:
                return None
            time.sleep(2 ** attempt)

    return None


def assess_match(company: dict, lead: dict) -> tuple[dict, str]:
    ai_result = assess_with_openai(company, lead)
    if ai_result:
        return ai_result, "openai"
    return local_rule_based_assessment(company, lead), "local_rules"


def save_match(company: dict, lead: dict, assessment: dict, source: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO matches
        (company_id, lead_id, company_name, lead_name, match_score, verdict, confidence, reasons, recommended_action, source, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            company["id"],
            lead["id"],
            assessment["company_name"],
            assessment["lead_name"],
            assessment["match_score"],
            assessment["verdict"],
            assessment["confidence"],
            json.dumps(assessment["reasons"], ensure_ascii=False),
            assessment["recommended_action"],
            source,
            now_iso(),
        ),
    )
    conn.commit()
    match_id = cur.lastrowid
    conn.close()
    return match_id


def hydrate_match(row):
    item = dict(row)
    try:
        item["reasons"] = json.loads(item.get("reasons") or "[]")
    except Exception:
        item["reasons"] = []
    return item


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/companies")
def list_companies():
    conn = get_db()
    rows = conn.execute("SELECT * FROM companies ORDER BY id").fetchall()
    conn.close()
    return jsonify(rows_to_dicts(rows))


@app.post("/api/companies")
def add_company():
    data = request.get_json(force=True)
    required = ["name", "industry", "location", "description"]
    missing = [key for key in required if not data.get(key)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO companies (name, email, industry, location, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (data["name"], data.get("email", ""), data["industry"], data["location"], data["description"], now_iso()),
    )
    conn.commit()
    company = conn.execute("SELECT * FROM companies WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(company)), 201


@app.get("/api/leads")
def list_leads():
    conn = get_db()
    rows = conn.execute("SELECT * FROM leads ORDER BY id").fetchall()
    conn.close()
    return jsonify(rows_to_dicts(rows))


@app.post("/api/leads")
def add_lead():
    data = request.get_json(force=True)
    required = ["name", "age", "city", "country", "working_status", "income_status"]
    missing = [key for key in required if data.get(key) in (None, "")]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO leads (name, email, age, gender, working_status, country, city, family, income_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["name"], data.get("email", ""), int(data["age"]), data.get("gender", ""),
            data["working_status"], data["country"], data["city"], data.get("family", ""),
            data["income_status"], now_iso(),
        ),
    )
    conn.commit()
    lead = conn.execute("SELECT * FROM leads WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(lead)), 201


@app.get("/api/matches")
def list_matches():
    limit = min(int(request.args.get("limit", 100)), 500)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM matches ORDER BY match_score DESC, created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return jsonify([hydrate_match(row) for row in rows])


@app.delete("/api/matches")
def clear_matches():
    conn = get_db()
    conn.execute("DELETE FROM matches")
    conn.commit()
    conn.close()
    return jsonify({"message": "All matches deleted."})


@app.post("/api/match/run")
def run_matches():
    data = request.get_json(silent=True) or {}
    company_id = data.get("company_id")
    lead_id = data.get("lead_id")

    conn = get_db()
    companies = rows_to_dicts(conn.execute(
        "SELECT * FROM companies WHERE id = ?" if company_id else "SELECT * FROM companies ORDER BY id",
        (company_id,) if company_id else (),
    ).fetchall())
    leads = rows_to_dicts(conn.execute(
        "SELECT * FROM leads WHERE id = ?" if lead_id else "SELECT * FROM leads ORDER BY id",
        (lead_id,) if lead_id else (),
    ).fetchall())
    conn.close()

    if not companies or not leads:
        return jsonify({"error": "No companies or leads found for the selected filter."}), 404

    created = []
    for company, lead in itertools.product(companies, leads):
        assessment, source = assess_match(company, lead)
        match_id = save_match(company, lead, assessment, source)
        assessment["id"] = match_id
        assessment["company_id"] = company["id"]
        assessment["lead_id"] = lead["id"]
        assessment["source"] = source
        created.append(assessment)

    created.sort(key=lambda item: item["match_score"], reverse=True)
    return jsonify({"count": len(created), "matches": created})


@app.get("/api/status")
def status():
    return jsonify({
        "database_path": DB_PATH,
        "openai_enabled": bool(USE_OPENAI and os.getenv("OPENAI_API_KEY") and OpenAI is not None),
        "model": MODEL,
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
else:
    init_db()
