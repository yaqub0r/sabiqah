PRAGMA foreign_keys = ON;

CREATE TABLE members (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  github_user_id TEXT NOT NULL UNIQUE,
  github_login TEXT NOT NULL,
  avatar_url TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'limited', 'suspended')),
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE reputation_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  subject_member_id INTEGER NOT NULL REFERENCES members(id),
  actor_member_id INTEGER REFERENCES members(id),
  event_type TEXT NOT NULL CHECK (event_type IN (
    'enrollment.completed',
    'review.submitted',
    'review.accepted',
    'review.rejected',
    'review.reversed',
    'moderation.limited',
    'moderation.suspended',
    'moderation.restored'
  )),
  book_slug TEXT,
  repository TEXT NOT NULL,
  external_ref TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(payload_json)),
  assessment_label TEXT,
  assessment_model TEXT,
  recorded_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE UNIQUE INDEX reputation_event_source
  ON reputation_events(repository, external_ref, event_type, subject_member_id);
CREATE INDEX reputation_event_subject_time
  ON reputation_events(subject_member_id, recorded_at DESC);

CREATE TRIGGER reputation_events_are_append_only_update
BEFORE UPDATE ON reputation_events
BEGIN
  SELECT RAISE(ABORT, 'reputation events are append-only');
END;

CREATE TRIGGER reputation_events_are_append_only_delete
BEFORE DELETE ON reputation_events
BEGIN
  SELECT RAISE(ABORT, 'reputation events are append-only');
END;

CREATE TABLE moderation_decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  subject_member_id INTEGER NOT NULL REFERENCES members(id),
  actor_member_id INTEGER NOT NULL REFERENCES members(id),
  previous_status TEXT NOT NULL,
  next_status TEXT NOT NULL CHECK (next_status IN ('active', 'limited', 'suspended')),
  reason TEXT NOT NULL,
  reputation_event_id INTEGER NOT NULL UNIQUE REFERENCES reputation_events(id),
  created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
