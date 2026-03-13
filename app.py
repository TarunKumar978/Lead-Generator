"""
Silasya & Shoumitra — AI Lead Finder
Flask + MySQL Backend
"""

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
import os
import json
import anthropic
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "silasya-secret-2025")
CORS(app)

# ─── DB Pool ─────────────────────────────────────────────────────────────────
db_config = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "silasya_leads"),
}

connection_pool = None

def get_pool():
    global connection_pool
    if connection_pool is None:
        connection_pool = pooling.MySQLConnectionPool(
            pool_name="silasya_pool",
            pool_size=5,
            **db_config
        )
    return connection_pool

def get_db():
    return get_pool().get_connection()

# ─── DB Init ─────────────────────────────────────────────────────────────────
def init_db():
    """Create database and tables if they don't exist."""
    # Connect without database first to create it
    conn = mysql.connector.connect(
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["user"],
        password=db_config["password"],
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_config['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute(f"USE `{db_config['database']}`")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            name         VARCHAR(255) NOT NULL,
            type         ENUM('b2c','b2b') NOT NULL DEFAULT 'b2c',
            category     VARCHAR(255),
            country      VARCHAR(100),
            city         VARCHAR(100),
            email        VARCHAR(255),
            phone        VARCHAR(100),
            website      VARCHAR(500),
            instagram    VARCHAR(255),
            linkedin     VARCHAR(500),
            facebook     VARCHAR(500),
            whatsapp     VARCHAR(100),
            description  TEXT,
            why_good     TEXT,
            potential_value VARCHAR(100),
            tags         JSON,
            score        INT DEFAULT 50,
            status       ENUM('new','warm','hot','contacted','converted','closed') DEFAULT 'new',
            source       VARCHAR(255),
            notes        TEXT,
            saved_by     VARCHAR(100),
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            business     VARCHAR(50),
            country      VARCHAR(255),
            niche        VARCHAR(255),
            lead_type    VARCHAR(255),
            channels     TEXT,
            keywords     TEXT,
            leads_found  INT DEFAULT 0,
            searched_by  VARCHAR(100),
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            name       VARCHAR(100) NOT NULL,
            email      VARCHAR(255) UNIQUE NOT NULL,
            role       ENUM('admin','member') DEFAULT 'member',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # Insert default team member if empty
    cursor.execute("SELECT COUNT(*) FROM team_members")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO team_members (name, email, role) VALUES ('Admin', 'admin@silasya.com', 'admin')")

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database initialized successfully")

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM leads")
        total = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify({"status": "ok", "total_leads": total, "db": "connected"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ── Leads CRUD ────────────────────────────────────────────────────────────────

@app.route("/api/leads", methods=["GET"])
def get_leads():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        type_filter = request.args.get("type")        # b2c / b2b
        status_filter = request.args.get("status")    # new / warm / hot etc
        search = request.args.get("search", "")
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        query = "SELECT * FROM leads WHERE 1=1"
        params = []

        if type_filter:
            query += " AND type = %s"
            params.append(type_filter)
        if status_filter:
            query += " AND status = %s"
            params.append(status_filter)
        if search:
            query += " AND (name LIKE %s OR email LIKE %s OR country LIKE %s OR category LIKE %s)"
            s = f"%{search}%"
            params.extend([s, s, s, s])

        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        leads = cursor.fetchall()

        # Convert tags JSON string to list
        for lead in leads:
            if isinstance(lead.get("tags"), str):
                try:
                    lead["tags"] = json.loads(lead["tags"])
                except:
                    lead["tags"] = []
            if lead.get("created_at"):
                lead["created_at"] = lead["created_at"].isoformat()
            if lead.get("updated_at"):
                lead["updated_at"] = lead["updated_at"].isoformat()

        # Get total count
        count_query = "SELECT COUNT(*) as cnt FROM leads WHERE 1=1"
        count_params = []
        if type_filter:
            count_query += " AND type = %s"; count_params.append(type_filter)
        if status_filter:
            count_query += " AND status = %s"; count_params.append(status_filter)
        if search:
            count_query += " AND (name LIKE %s OR email LIKE %s OR country LIKE %s OR category LIKE %s)"
            s = f"%{search}%"; count_params.extend([s,s,s,s])

        cursor.execute(count_query, count_params)
        total = cursor.fetchone()["cnt"]

        cursor.close()
        conn.close()
        return jsonify({"leads": leads, "total": total, "limit": limit, "offset": offset})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/leads", methods=["POST"])
def save_lead():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        conn = get_db()
        cursor = conn.cursor()

        tags = json.dumps(data.get("tags", []))
        score = int(data.get("score", 50))
        status = "hot" if score >= 80 else "warm" if score >= 60 else "new"

        cursor.execute("""
            INSERT INTO leads 
            (name, type, category, country, city, email, phone, website,
             instagram, linkedin, facebook, whatsapp, description, why_good,
             potential_value, tags, score, status, source, notes, saved_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data.get("name", "Unknown"),
            data.get("type", "b2c"),
            data.get("category", ""),
            data.get("country", ""),
            data.get("city", ""),
            data.get("email", ""),
            data.get("phone", ""),
            data.get("website", ""),
            data.get("instagram", ""),
            data.get("linkedin", ""),
            data.get("facebook", ""),
            data.get("whatsapp", ""),
            data.get("description", ""),
            data.get("why_good_lead", ""),
            data.get("potential_value", ""),
            tags,
            score,
            status,
            data.get("source", "AI Search"),
            data.get("notes", ""),
            data.get("saved_by", "Team"),
        ))

        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({"success": True, "id": new_id, "message": "Lead saved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/leads/bulk", methods=["POST"])
def save_leads_bulk():
    try:
        data = request.get_json()
        leads_list = data.get("leads", [])
        saved_by = data.get("saved_by", "Team")

        if not leads_list:
            return jsonify({"error": "No leads provided"}), 400

        conn = get_db()
        cursor = conn.cursor()
        saved = 0

        for lead in leads_list:
            tags = json.dumps(lead.get("tags", []))
            score = int(lead.get("score", 50))
            status = "hot" if score >= 80 else "warm" if score >= 60 else "new"

            # Skip duplicates by email
            if lead.get("email"):
                cursor.execute("SELECT id FROM leads WHERE email = %s", (lead["email"],))
                if cursor.fetchone():
                    continue

            cursor.execute("""
                INSERT INTO leads 
                (name, type, category, country, city, email, phone, website,
                 instagram, linkedin, facebook, whatsapp, description, why_good,
                 potential_value, tags, score, status, source, saved_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                lead.get("name","Unknown"), lead.get("type","b2c"),
                lead.get("category",""), lead.get("country",""), lead.get("city",""),
                lead.get("email",""), lead.get("phone",""), lead.get("website",""),
                lead.get("instagram",""), lead.get("linkedin",""), lead.get("facebook",""),
                lead.get("whatsapp",""), lead.get("description",""),
                lead.get("why_good_lead",""), lead.get("potential_value",""),
                tags, score, status, lead.get("source","AI Search"), saved_by,
            ))
            saved += 1

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "saved": saved, "message": f"{saved} leads saved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/leads/<int:lead_id>", methods=["PUT"])
def update_lead(lead_id):
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()

        fields = []
        values = []
        allowed = ["status","notes","score","email","phone","website","instagram","linkedin","facebook","whatsapp"]
        for f in allowed:
            if f in data:
                fields.append(f"{f} = %s")
                values.append(data[f])

        if not fields:
            return jsonify({"error": "Nothing to update"}), 400

        values.append(lead_id)
        cursor.execute(f"UPDATE leads SET {', '.join(fields)} WHERE id = %s", values)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/leads/<int:lead_id>", methods=["DELETE"])
def delete_lead(lead_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM leads WHERE id = %s", (lead_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Stats ─────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def get_stats():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as total FROM leads")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as cnt FROM leads WHERE type='b2c'")
        b2c = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM leads WHERE type='b2b'")
        b2b = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM leads WHERE score >= 80")
        hot = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM leads WHERE score >= 60 AND score < 80")
        warm = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(DISTINCT country) as cnt FROM leads WHERE country != ''")
        countries = cursor.fetchone()["cnt"]

        cursor.execute("""
            SELECT status, COUNT(*) as cnt FROM leads GROUP BY status
        """)
        status_counts = {r["status"]: r["cnt"] for r in cursor.fetchall()}

        cursor.execute("""
            SELECT source, COUNT(*) as cnt FROM leads 
            WHERE source != '' GROUP BY source ORDER BY cnt DESC LIMIT 5
        """)
        top_sources = cursor.fetchall()

        cursor.execute("""
            SELECT country, COUNT(*) as cnt FROM leads 
            WHERE country != '' GROUP BY country ORDER BY cnt DESC LIMIT 5
        """)
        top_countries = cursor.fetchall()

        cursor.close()
        conn.close()
        return jsonify({
            "total": total, "b2c": b2c, "b2b": b2b,
            "hot": hot, "warm": warm, "countries": countries,
            "status_counts": status_counts,
            "top_sources": top_sources,
            "top_countries": top_countries,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── AI Search ─────────────────────────────────────────────────────────────────

@app.route("/api/search", methods=["POST"])
def ai_search():
    try:
        data = request.get_json()
        business  = data.get("business", "both")
        country   = data.get("country", "India and worldwide")
        niche     = data.get("niche", "organic products")
        lead_type = data.get("lead_type", "all")
        channels  = data.get("channels", "Google, LinkedIn, Instagram")
        keywords  = data.get("keywords", "")
        saved_by  = data.get("saved_by", "Team")

        # Log search
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO search_history (business, country, niche, lead_type, channels, keywords, searched_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (business, country, niche, lead_type, channels, keywords, saved_by))
        conn.commit()
        cursor.close()
        conn.close()

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        prompt = f"""You are a professional B2B and B2C lead generation expert for two Indian organic businesses:
1. SILASYA (B2C) — sells 100% organic apparel, toys, home décor to end customers
2. SHOUMITRA (B2B) — exports same products globally to wholesalers, importers, retailers, boutiques, NGOs

Generate 12 highly specific, realistic leads based on:
- Business: {business}
- Target country/region: {country}
- Product niche: {niche}
- Lead type: {lead_type}
- Channels searched: {channels}
- Extra keywords: {keywords or 'none'}

Return ONLY a valid JSON array — no markdown, no explanation, just raw JSON.

Each lead object must have:
{{
  "name": "Company or person full name",
  "type": "b2c or b2b",
  "category": "matching product category",
  "country": "country name",
  "city": "city name",
  "description": "2-3 sentences about who they are and relevance",
  "source": "where found: LinkedIn / Instagram / IndiaMART / Google / Alibaba / Etsy / FabIndia / TradeIndia etc",
  "website": "full URL",
  "email": "contact email",
  "phone": "phone number with country code",
  "instagram": "@handle",
  "linkedin": "full LinkedIn URL",
  "facebook": "full Facebook URL",
  "whatsapp": "whatsapp number",
  "tags": ["tag1", "tag2", "tag3"],
  "why_good_lead": "one sentence on why valuable for Silasya/Shoumitra",
  "score": integer 50-98,
  "potential_value": "e.g. ₹5,000-15,000 or $10,000-50,000"
}}

Rules:
- Make leads feel REAL — use realistic names, real-sounding cities, actual-style URLs
- Mix B2C + B2B if business is 'both', else match requested type
- B2B: importers, wholesalers, eco-chains, fair trade orgs, boutique buyers
- B2C: organic lifestyle buyers, gifting customers, eco-conscious shoppers
- Vary countries based on target region
- Score 85-98 for full contact info + high relevance
- Return exactly 12 leads as a JSON array"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = message.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1:
            raw = raw[start:end+1]

        leads = json.loads(raw)

        # Update search history with count
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE search_history SET leads_found = %s 
            WHERE id = (SELECT MAX(id) FROM search_history WHERE searched_by = %s)
        """, (len(leads), saved_by))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True, "leads": leads, "count": len(leads)})

    except json.JSONDecodeError as e:
        return jsonify({"error": f"AI returned invalid data: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── AI Outreach ───────────────────────────────────────────────────────────────

@app.route("/api/outreach/<int:lead_id>", methods=["POST"])
def generate_outreach(lead_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM leads WHERE id = %s", (lead_id,))
        lead = cursor.fetchone()
        cursor.close()
        conn.close()

        if not lead:
            return jsonify({"error": "Lead not found"}), 404

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        if lead["type"] == "b2c":
            prompt = f"""Write multi-platform outreach messages for this B2C lead for SILASYA (100% organic brand — apparel, toys, décor).

Lead: {lead['name']}, Country: {lead['country']}, City: {lead.get('city','')}, Category: {lead['category']}
Description: {lead['description']}
Platforms available: WhatsApp: {'yes' if lead.get('whatsapp') else 'no'}, Instagram: {'yes' if lead.get('instagram') else 'no'}, Facebook: {'yes' if lead.get('facebook') else 'no'}, LinkedIn: {'yes' if lead.get('linkedin') else 'no'}, Email: {'yes' if lead.get('email') else 'no'}

Write clearly labeled messages:
📲 WHATSAPP (warm, personal, max 120 words)
📸 INSTAGRAM DM (casual, max 70 words)  
👤 FACEBOOK MESSAGE (friendly, max 100 words)
✉️ EMAIL (subject + body, max 150 words)
📅 3 FOLLOW-UP messages (Day 3, Day 7, Day 14)"""
        else:
            prompt = f"""Write multi-platform outreach for this B2B export lead for SHOUMITRA (Indian organic exporter — apparel, toys, décor, handcrafted).

Lead: {lead['name']}, Country: {lead['country']}, Category: {lead['category']}
Description: {lead['description']}
Potential value: {lead.get('potential_value','')}

Write clearly labeled messages:
✉️ EMAIL (subject + body, professional, max 200 words)
💼 LINKEDIN INMAIL (formal, max 120 words)
📲 WHATSAPP BUSINESS (concise, max 90 words)
📸 INSTAGRAM/FACEBOOK DM (casual, max 70 words)
📅 FOLLOW-UP SEQUENCE (Day 3, Day 7, Day 14)

Shoumitra USPs: 100% organic, export-ready, globally compliant, no minimum order, GOTS/OEKO-TEX certifiable."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        return jsonify({"success": True, "outreach": message.content[0].text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Team Members ──────────────────────────────────────────────────────────────

@app.route("/api/team", methods=["GET"])
def get_team():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, role, created_at FROM team_members ORDER BY created_at")
        members = cursor.fetchall()
        for m in members:
            if m.get("created_at"):
                m["created_at"] = m["created_at"].isoformat()
        cursor.close()
        conn.close()
        return jsonify({"members": members})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/team", methods=["POST"])
def add_team_member():
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO team_members (name, email, role) VALUES (%s, %s, %s)",
            (data["name"], data["email"], data.get("role","member"))
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except mysql.connector.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Export ────────────────────────────────────────────────────────────────────

@app.route("/api/export/csv")
def export_csv():
    try:
        import csv, io
        from flask import Response

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM leads ORDER BY created_at DESC")
        leads = cursor.fetchall()
        cursor.close()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID","Type","Name","Email","Phone","Country","City","Category",
                         "Website","Instagram","LinkedIn","Facebook","WhatsApp",
                         "Score","Status","Source","Potential Value","Description","Notes","Saved By","Date"])
        for l in leads:
            writer.writerow([
                l["id"], l["type"], l["name"], l["email"], l["phone"],
                l["country"], l["city"], l["category"], l["website"],
                l["instagram"], l["linkedin"], l["facebook"], l["whatsapp"],
                l["score"], l["status"], l["source"], l["potential_value"],
                l["description"], l["notes"], l["saved_by"],
                l["created_at"].isoformat() if l.get("created_at") else ""
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=silasya_shoumitra_leads.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Starting Silasya & Shoumitra Lead Finder...")
    print("📦 Initializing database...")
    init_db()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    print(f"✅ App running at http://localhost:{port}")
    print(f"📋 Share with team: http://YOUR_IP:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
