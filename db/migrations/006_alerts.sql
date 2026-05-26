-- Alerts emitted by the continuous monitor agent. One row per
-- (region, disruptor-mix, threshold-crossing) — deduped by composite key.
CREATE TABLE IF NOT EXISTS alerts (
    id              BIGSERIAL PRIMARY KEY,
    region_id       INT REFERENCES regions(id),
    severity_score  REAL    NOT NULL,                 -- weighted score that tripped the threshold
    threshold       REAL    NOT NULL,
    top_disruptors  JSONB   NOT NULL,                 -- {disruptor: severity}
    ipc_phase_6mo   REAL,                             -- model projection at trip time, if available
    triggered_at    TIMESTAMPTZ DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    UNIQUE (region_id, triggered_at)
);
CREATE INDEX IF NOT EXISTS alerts_region_idx ON alerts (region_id, triggered_at DESC);
CREATE INDEX IF NOT EXISTS alerts_open_idx   ON alerts (region_id) WHERE resolved_at IS NULL;
