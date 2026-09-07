-- Intent confidence for active learning (gói F, 06/09).
--
-- The trained intent classifier already produces a top-class probability at
-- ingest time but the schema dropped it. Persisting it enables the planned
-- active-learning loop (docs/benchmarks/llm-labeling.md): export the
-- least-confident comments FIRST for LLM/human labeling. NULL means the
-- keyword baseline classified the row (it has no probability model) or the
-- row predates this migration.

ALTER TABLE comment_event ADD COLUMN intent_confidence real;
