"""
Silasya & Shumitra — AI Lead Finder
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

    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db_config['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )

    cursor.execute(f"USE `{db_config['database']}`")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            type ENUM('b2c','b2b') NOT NULL DEFAULT 'b2c',
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
            status ENUM('new','warm','hot','contacted','converted','closed') DEFAULT 'new',
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
            role ENUM('admin','member') DEFAULT 'member',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("SELECT COUNT(*) FROM team_members")

    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO team_members (name, email, role)
            VALUES ('Admin', 'admin@silasya.com', 'admin')
        """)

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

        return jsonify({
            "status": "ok",
            "total_leads": total,
            "db": "connected"
        })

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
            INSERT INTO search_history
            (business, country, niche, lead_type, channels, keywords, searched_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (business, country, niche, lead_type, channels, keywords, saved_by))

        conn.commit()

        # Clean old history (keep last 100 searches)

        cursor.execute("""
        DELETE FROM search_history
        WHERE id NOT IN (
            SELECT id FROM (
                SELECT id
                FROM search_history
                ORDER BY created_at DESC
                LIMIT 100
            ) AS tmp
        )
        """)

        conn.commit()

        cursor.close()
        conn.close()

        client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        prompt = f"""Generate 12 realistic B2B/B2C leads.

Business: {business}
Country: {country}
Niche: {niche}
Lead type: {lead_type}
Channels: {channels}
Keywords: {keywords}

Return ONLY JSON array.
"""

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

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE search_history SET leads_found = %s
            WHERE id = (
                SELECT id FROM (
                    SELECT id
                    FROM search_history
                    WHERE searched_by = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                ) AS tmp
            )
        """, (len(leads), saved_by))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "leads": leads,
            "count": len(leads)
        })

    except json.JSONDecodeError as e:
        return jsonify({"error": f"AI returned invalid data: {str(e)}"}), 500

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

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug
    )