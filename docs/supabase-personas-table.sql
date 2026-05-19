-- Run this in Supabase: SQL Editor → New query → paste → Run
-- This creates the personas table used by "My persona" (bio, discipline).
-- Table name is "personas" (not "profile"). After running, you'll see it under Table Editor.
--
-- How it links to Auth:
--   personas.user_id = the same UUID as in Authentication → Users (auth.users.id).
--   A row is only created when you successfully click Save in "My persona" in the app.
--   If you see yourself in Authentication but not in personas, auth is working but
--   no successful save has happened yet (fix "Authentication required" then save again).

CREATE TABLE IF NOT EXISTS personas (
    user_id TEXT PRIMARY KEY,
    username TEXT DEFAULT '',
    discipline TEXT DEFAULT '',
    bio TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    papers_of_interest TEXT DEFAULT '',
    concepts_focus TEXT DEFAULT '',
    methods_focus TEXT DEFAULT '',
    tech_stack TEXT DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- If the table existed before the personalization update, add the new columns:
ALTER TABLE personas ADD COLUMN IF NOT EXISTS username TEXT DEFAULT '';
ALTER TABLE personas ADD COLUMN IF NOT EXISTS tags TEXT DEFAULT '';
ALTER TABLE personas ADD COLUMN IF NOT EXISTS papers_of_interest TEXT DEFAULT '';
ALTER TABLE personas ADD COLUMN IF NOT EXISTS concepts_focus TEXT DEFAULT '';
ALTER TABLE personas ADD COLUMN IF NOT EXISTS methods_focus TEXT DEFAULT '';
ALTER TABLE personas ADD COLUMN IF NOT EXISTS tech_stack TEXT DEFAULT '';

-- Optional: view that links personas to auth users by email (so you can see who is who).
-- Run this only if you want a "personas_with_email" view in Table Editor.
/*
CREATE OR REPLACE VIEW personas_with_email AS
SELECT p.user_id, p.discipline, p.bio, p.updated_at, u.email
FROM public.personas p
LEFT JOIN auth.users u ON u.id::text = p.user_id;
*/
