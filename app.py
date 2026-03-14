"""
Silasya & Shoumitra — AI Lead Finder
Flask + MySQL Backend
"""

from flask import Flask, request, jsonify, render_template, session, Response
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
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
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
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(10) DEFAULT 'b2c',
            category VARCHAR(255),
            country VARCHAR(100),
            city VARCHAR(100),
            email VARCHAR(255),
            phone VARCHAR(100),
            website VARCHAR(500),
            instagram VARCHAR(255),
            linkedin VARCHAR(500),
            facebook VARCHAR(500),
            whatsapp VARCHAR(100),
            description TEXT,
            why_good TEXT,
            potential_value VARCHAR(100),
            tags JSON,
            score INT DEFAULT 50,
            status VARCHAR(50) DEFAULT 'new',
            source VARCHAR(255),
            notes TEXT,
            saved_by VARCHAR(100),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            business VARCHAR(50),
            country VARCHAR(255),
            niche VARCHAR(255),
            lead_type VARCHAR(255),
            channels TEXT,
            keywords TEXT,
            leads_found INT DEFAULT 0,
            searched_by VARCHAR(100),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            role VARCHAR(20) DEFAULT 'member',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
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


# ─── AI Search ───────────────────────────────────────────────────────────────

@app.route("/api/search", methods=["POST"])
def ai_search():
    try:
        data = request.get_json()
        business = data.get("business", "both")
        country = data.get("country", "India and worldwide")
        niche = data.get("niche", "organic products")
        lead_type = data.get("lead_type", "all")
        channels = data.get("channels", "Google, LinkedIn, Instagram")
        keywords = data.get("keywords", "")
        saved_by = data.get("saved_by", "Team")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO search_history (business, country, niche, lead_type, channels, keywords, searched_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (business, country, niche, lead_type, channels, keywords, saved_by))
        conn.commit()
        search_id = cursor.lastrowid

        cursor.execute("""
            DELETE FROM search_history WHERE id NOT IN (
                SELECT id FROM (SELECT id FROM search_history ORDER BY created_at DESC LIMIT 100) AS tmp
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        prompt = f"""You are a lead generation expert for two Indian organic businesses:
- SILASYA: B2C organic apparel, toys, home decor brand
- SHOUMITRA: B2B export arm selling organic products worldwide

Generate 12 realistic, detailed leads based on these parameters:
Business Focus: {business}
Target Country/Region: {country}
Product Niche: {niche}
Lead Type: {lead_type}
Search Channels: {channels}
Extra Keywords: {keywords}

Return ONLY a valid JSON array with exactly 12 leads. Each lead must have these fields:
- name (string): Company or person name
- type (string): "b2c" or "b2b"
- category (string): e.g. "Organic Retailer", "Eco Store", "Wholesale Buyer"
- country (string)
- city (string)
- email (string): realistic email
- phone (string): realistic phone with country code
- website (string): realistic URL
- instagram (string): @handle
- linkedin (string): LinkedIn URL
- whatsapp (string): phone number
- description (string): 1-2 sentence description
- why_good (string): why this is a good lead for Silasya/Shoumitra
- potential_value (string): e.g. "High", "Medium", "$5,000-$10,000/month"
- score (number): 1-100 lead quality score
- tags (array of strings): relevant tags
- source (string): where this lead was found

Return ONLY the JSON array, no other text."""

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
        cursor.execute("UPDATE search_history SET leads_found = %s WHERE id = %s", (len(leads), search_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True, "leads": leads, "count": len(leads)})

    except json.JSONDecodeError as e:
        return jsonify({"error": f"AI returned invalid data: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Save Lead ───────────────────────────────────────────────────────────────

@app.route("/api/leads", methods=["GET"])
def get_leads():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        status_filter = request.args.get("status", "")
        type_filter = request.args.get("type", "")
        search = request.args.get("search", "")

        query = "SELECT * FROM leads WHERE 1=1"
        params = []

        if status_filter:
            query += " AND status = %s"
            params.append(status_filter)
        if type_filter:
            query += " AND type = %s"
            params.append(type_filter)
        if search:
            query += " AND (name LIKE %s OR email LIKE %s OR country LIKE %s OR category LIKE %s)"
            s = f"%{search}%"
            params.extend([s, s, s, s])

        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        leads = cursor.fetchall()

        for lead in leads:
            if lead.get("tags") and isinstance(lead["tags"], str):
                try:
                    lead["tags"] = json.loads(lead["tags"])
                except:
                    lead["tags"] = []
            if lead.get("created_at"):
                lead["created_at"] = lead["created_at"].isoformat()
            if lead.get("updated_at"):
                lead["updated_at"] = lead["updated_at"].isoformat()

        cursor.close()
        conn.close()
        return jsonify({"success": True, "leads": leads, "count": len(leads)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/leads", methods=["POST"])
def save_lead():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        name = data.get("name") or "Unknown Lead"
        tags = data.get("tags", [])
        if isinstance(tags, list):
            tags = json.dumps(tags)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO leads (name, type, category, country, city, email, phone, website,
                instagram, linkedin, facebook, whatsapp, description, why_good,
                potential_value, tags, score, status, source, saved_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            name,
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
            data.get("why_good", ""),
            data.get("potential_value", ""),
            tags,
            int(data.get("score", 50)),
            data.get("status", "new"),
            data.get("source", "AI Search"),
            data.get("saved_by", "Team"),
        ))
        conn.commit()
        lead_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return jsonify({"success": True, "id": lead_id, "message": f"Lead '{name}' saved!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/leads/<int:lead_id>", methods=["PUT"])
def update_lead(lead_id):
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE leads SET status=%s, notes=%s WHERE id=%s
        """, (data.get("status", "new"), data.get("notes", ""), lead_id))
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
        cursor.execute("DELETE FROM leads WHERE id=%s", (lead_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Stats ───────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def get_stats():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as total FROM leads")
        total = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) as hot FROM leads WHERE score >= 80")
        hot = cursor.fetchone()["hot"]
        cursor.execute("SELECT COUNT(*) as converted FROM leads WHERE status = 'converted'")
        converted = cursor.fetchone()["converted"]
        cursor.execute("SELECT COUNT(DISTINCT country) as countries FROM leads")
        countries = cursor.fetchone()["countries"]
        cursor.close()
        conn.close()
        return jsonify({"total": total, "hot": hot, "converted": converted, "countries": countries})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Export CSV ──────────────────────────────────────────────────────────────

@app.route("/api/export/csv")
def export_csv():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM leads ORDER BY created_at DESC")
        leads = cursor.fetchall()
        cursor.close()
        conn.close()

        lines = ["Name,Type,Category,Country,City,Email,Phone,Website,Score,Status,Saved By,Created At"]
        for l in leads:
            lines.append(f'"{l.get("name","")}", "{l.get("type","")}", "{l.get("category","")}", "{l.get("country","")}", "{l.get("city","")}", "{l.get("email","")}", "{l.get("phone","")}", "{l.get("website","")}", "{l.get("score","")}", "{l.get("status","")}", "{l.get("saved_by","")}", "{l.get("created_at","")}"')

        csv = "\n".join(lines)
        return Response(csv, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=silasya_leads.csv"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Team ────────────────────────────────────────────────────────────────────

@app.route("/api/team", methods=["GET"])
def get_team():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM team_members ORDER BY created_at")
        members = cursor.fetchall()
        for m in members:
            if m.get("created_at"):
                m["created_at"] = m["created_at"].isoformat()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "members": members})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/team", methods=["POST"])
def add_team():
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO team_members (name, email, role) VALUES (%s,%s,%s)
        """, (data.get("name"), data.get("email"), data.get("role", "member")))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── AI Outreach ─────────────────────────────────────────────────────────────

@app.route("/api/outreach/<int:lead_id>", methods=["POST"])
def generate_outreach(lead_id):
    try:
        data = request.get_json()
        channel = data.get("channel", "email")

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM leads WHERE id=%s", (lead_id,))
        lead = cursor.fetchone()
        cursor.close()
        conn.close()

        if not lead:
            return jsonify({"error": "Lead not found"}), 404

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        prompt = f"""Write a {channel} outreach message for this lead on behalf of Silasya & Shoumitra (Indian organic brand).

Lead: {lead.get('name')}
Type: {lead.get('type')}
Category: {lead.get('category')}
Country: {lead.get('country')}
Description: {lead.get('description')}

Write a short, friendly, professional {channel} message. Keep it under 150 words."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        return jsonify({"success": True, "message": message.content[0].text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Starting Silasya & Shoumitra Lead Finder...")
    print("📦 Initializing database...")
    init_db()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    print(f"✅ App running at http://localhost:{port}")
    print(f"📋 Share with team: http://YOUR_IP:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
