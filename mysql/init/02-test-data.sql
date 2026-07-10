-- Seed data initialization script
-- Runs after 01-init-db.sql due to alphabetical ordering
--
-- NOTE: The owner account is seeded with a PLACEHOLDER password
--       hash that cannot be logged in with. Replace it with a real hash
--       (or run api/seed_owner.py instead) before using the account.
--
-- To generate a hash:
--   python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('yourpassword'))"

USE app_db;

-- Owner account: owner (owner@example.com) — change to your own username/email.
-- Password hash is a placeholder — replace it before use (see NOTE above).
-- Seeded with email verified so you can test everything immediately.
INSERT INTO user (username, email, password_hash, email_verified, terms_accepted,
                  is_admin)
VALUES ('owner', 'owner@example.com',
        'pbkdf2:sha256:600000$PLACEHOLDER$0000000000000000000000000000000000000000000000000000000000000000',
        TRUE, TRUE, TRUE);

-- Preferences
INSERT INTO user_preferences (user_id, game_type, art_style, rating)
VALUES (1, 'fantasy_dnd', 'frazetta', 'pg13');
