-- Database initialization script
-- Creates the base schema for Town Scryer

USE app_db;

-- Create user table
CREATE TABLE IF NOT EXISTS user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255),
    verification_sent_at TIMESTAMP NULL,
    terms_accepted BOOLEAN DEFAULT FALSE,
    terms_accepted_at TIMESTAMP NULL,
    pending_email VARCHAR(120),
    pending_email_token VARCHAR(255),
    invite_token VARCHAR(255),
    invited_by INT,
    admin_permissions TEXT,
    avatar VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    deactivated_at TIMESTAMP NULL,
    -- Usage tracking
    monthly_image_count INT DEFAULT 0,
    monthly_session_count INT DEFAULT 0,
    monthly_image_reset_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create terms_content table (admin-managed terms & conditions)
CREATE TABLE IF NOT EXISTS terms_content (
    id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT NOT NULL,
    version INT NOT NULL DEFAULT 1,
    updated_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Seed default terms
INSERT INTO terms_content (content, version) VALUES (
    'These are the placeholder terms and conditions for this application. The administrator can update these at any time from the admin panel.',
    1
);

-- Create page_hit table
CREATE TABLE IF NOT EXISTS page_hit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    path VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    referrer VARCHAR(500),
    user_agent VARCHAR(500),
    blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create game_table table
CREATE TABLE IF NOT EXISTS game_table (
    id INT AUTO_INCREMENT PRIMARY KEY,
    owner_user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    invite_code VARCHAR(6) UNIQUE NOT NULL,
    -- Per-table session defaults so the DM doesn't re-pick them every time.
    game_type VARCHAR(50) DEFAULT 'Fantasy D&D',
    art_style VARCHAR(50) DEFAULT 'Frazetta',
    rating VARCHAR(10) DEFAULT 'PG-13',
    -- Whether the Display (TV) view shows the AI-generated caption overlay.
    show_captions BOOLEAN DEFAULT TRUE,
    show_daub_updates BOOLEAN DEFAULT TRUE,
    -- Wake-word name. Lines that address her by name are treated as direct
    -- DM commands. Per-table override; default "Drongo".
    scryer_name VARCHAR(50) DEFAULT 'Daub',
    -- Scene-extract Claude model for sessions on this table. NULL = system
    -- default (env SCENE_MODEL_DEFAULT, then Haiku fallback).
    scene_model VARCHAR(80) NULL,
    -- Free-form DM scratchpad: lore, recurring NPC notes, world state.
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Create npc table (recurring non-player characters scoped to a game_table).
CREATE TABLE IF NOT EXISTS npc (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    portrait_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (table_id) REFERENCES game_table(id) ON DELETE CASCADE,
    INDEX idx_npc_table_id (table_id)
);

-- Create table_member table
CREATE TABLE IF NOT EXISTS table_member (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_id INT NOT NULL,
    user_id INT NOT NULL,
    role VARCHAR(10) NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_table_user (table_id, user_id),
    FOREIGN KEY (table_id) REFERENCES game_table(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Create session table
CREATE TABLE IF NOT EXISTS session (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    table_id INT,
    session_token VARCHAR(36) UNIQUE NOT NULL,
    last_heartbeat TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active', 'paused', 'ended') DEFAULT 'active',
    image_count INT DEFAULT 0,
    regen_count INT DEFAULT 0,
    api_call_count INT DEFAULT 0,
    estimated_cost_cents INT DEFAULT 0,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    max_duration_minutes INT DEFAULT 480,
    game_type VARCHAR(50) DEFAULT 'fantasy_dnd',
    art_style VARCHAR(50) DEFAULT 'frazetta',
    rating VARCHAR(10) DEFAULT 'PG-13',
    -- Quality signal. Higher = worse session run. +20 per DM correction,
    -- +10 per regen, -10 per scene naturally accepted (replaced by next).
    quality_score INT DEFAULT 0,
    -- Snapshot of the model that handled scene extraction for this session.
    scene_model VARCHAR(80) NULL,
    -- 30s cooldown anchor for the user-triggered "Make A New Image" path.
    last_change_image_at DATETIME NULL,
    -- Set while a fal call is in flight; Display flips to "Daub is
    -- painting…" while this is recent and non-null.
    generation_started_at DATETIME NULL,
    -- Rolling buffer of Whisper transcripts since session start; used by
    -- regen / Make-A-New-Image to re-interpret from fresh context.
    transcript_buffer TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (table_id) REFERENCES game_table(id) ON DELETE SET NULL
);

-- Create scene table
CREATE TABLE IF NOT EXISTS scene (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    image_path VARCHAR(500),
    prompt TEXT NOT NULL,
    scene_description TEXT,
    -- Short one-line caption for storybook-style display under the image.
    caption VARCHAR(200),
    -- Persistent location label (e.g. "forest campsite") — inherited from the
    -- previous scene unless Claude reports an explicit location change.
    location VARCHAR(150),
    -- DM gave this image the explicit nod (-15 quality_score on toggle).
    thumbs_up BOOLEAN DEFAULT FALSE,
    transcript_chunk TEXT,
    generation_time_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES session(id) ON DELETE CASCADE
);

-- Create session_correction table
CREATE TABLE IF NOT EXISTS session_correction (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    text VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES session(id) ON DELETE CASCADE
);

-- Create player_character table
CREATE TABLE IF NOT EXISTS player_character (
    id INT AUTO_INCREMENT PRIMARY KEY,
    -- user_id nullable: DM may pre-create unclaimed characters for players.
    -- A character can remain unclaimed forever; claiming is optional.
    user_id INT NULL,
    table_id INT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    portrait_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_table_char (user_id, table_id),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE SET NULL,
    FOREIGN KEY (table_id) REFERENCES game_table(id) ON DELETE SET NULL
);

-- Create user_preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    game_type VARCHAR(50) DEFAULT 'fantasy_dnd',
    art_style VARCHAR(50) DEFAULT 'frazetta',
    rating VARCHAR(10) DEFAULT 'PG-13',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_session_user_id ON session(user_id);
CREATE INDEX idx_session_status ON session(status);
CREATE INDEX idx_session_started_at ON session(started_at);
CREATE INDEX idx_scene_session_id ON scene(session_id);
CREATE INDEX idx_scene_created_at ON scene(created_at);
CREATE INDEX idx_player_character_user_id ON player_character(user_id);
CREATE INDEX idx_game_table_owner ON game_table(owner_user_id);
CREATE INDEX idx_game_table_invite_code ON game_table(invite_code);
CREATE INDEX idx_table_member_table_id ON table_member(table_id);
CREATE INDEX idx_table_member_user_id ON table_member(user_id);
CREATE INDEX idx_session_table_id ON session(table_id);
CREATE INDEX idx_player_character_table_id ON player_character(table_id);
CREATE INDEX idx_session_correction_session_id ON session_correction(session_id);
