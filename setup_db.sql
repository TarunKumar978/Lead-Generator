-- ─────────────────────────────────────────────────────────
--  Silasya & Shoumitra — Database Setup Script
--  Run this in MySQL Workbench or MySQL CLI:
--  mysql -u root -p < setup_db.sql
-- ─────────────────────────────────────────────────────────

CREATE DATABASE IF NOT EXISTS silasya_leads
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE silasya_leads;

CREATE TABLE IF NOT EXISTS leads (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(255)    NOT NULL,
    type            ENUM('b2c','b2b') NOT NULL DEFAULT 'b2c',
    category        VARCHAR(255),
    country         VARCHAR(100),
    city            VARCHAR(100),
    email           VARCHAR(255),
    phone           VARCHAR(100),
    website         VARCHAR(500),
    instagram       VARCHAR(255),
    linkedin        VARCHAR(500),
    facebook        VARCHAR(500),
    whatsapp        VARCHAR(100),
    description     TEXT,
    why_good        TEXT,
    potential_value VARCHAR(100),
    tags            JSON,
    score           INT             DEFAULT 50,
    status          ENUM('new','warm','hot','contacted','converted','closed') DEFAULT 'new',
    source          VARCHAR(255),
    notes           TEXT,
    saved_by        VARCHAR(100),
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type   (type),
    INDEX idx_status (status),
    INDEX idx_score  (score),
    INDEX idx_country(country)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS search_history (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    business    VARCHAR(50),
    country     VARCHAR(255),
    niche       VARCHAR(255),
    lead_type   VARCHAR(255),
    channels    TEXT,
    keywords    TEXT,
    leads_found INT             DEFAULT 0,
    searched_by VARCHAR(100),
    created_at  DATETIME        DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS team_members (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100)    NOT NULL,
    email       VARCHAR(255)    UNIQUE NOT NULL,
    role        ENUM('admin','member') DEFAULT 'member',
    created_at  DATETIME        DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Default admin
INSERT IGNORE INTO team_members (name, email, role)
VALUES ('Admin', 'admin@silasya.com', 'admin');

SELECT 'Database setup complete!' AS status;
