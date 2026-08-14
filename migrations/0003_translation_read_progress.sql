PRAGMA foreign_keys = ON;

CREATE TABLE translation_read_progress (
  member_id INTEGER NOT NULL REFERENCES members(id),
  corpus_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  read_at INTEGER NOT NULL DEFAULT (unixepoch()),
  PRIMARY KEY (member_id, corpus_id, item_id)
);

CREATE INDEX translation_read_progress_corpus_member
  ON translation_read_progress(corpus_id, member_id, read_at DESC);
