PRAGMA foreign_keys = ON;

CREATE TABLE translation_review_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reviewer_member_id INTEGER NOT NULL REFERENCES members(id),
  corpus_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('approve', 'withdraw')),
  item_sha256 TEXT NOT NULL CHECK (
    length(item_sha256) = 64 AND item_sha256 NOT GLOB '*[^0-9a-f]*'
  ),
  recorded_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX translation_review_latest
  ON translation_review_events(corpus_id, item_id, reviewer_member_id, id DESC);
CREATE INDEX translation_review_reviewer_time
  ON translation_review_events(reviewer_member_id, recorded_at DESC);

CREATE TRIGGER translation_review_events_are_append_only_update
BEFORE UPDATE ON translation_review_events
BEGIN
  SELECT RAISE(ABORT, 'translation review events are append-only');
END;

CREATE TRIGGER translation_review_events_are_append_only_delete
BEFORE DELETE ON translation_review_events
BEGIN
  SELECT RAISE(ABORT, 'translation review events are append-only');
END;
