-- FEWS NET / IPC observations: per-region food-insecurity phase per period.
-- Used as supervised-learning targets for the projector (3/6/12mo horizons).
--
-- ipc_phase: 1..5 IPC Acute Food Insecurity classification
--   1 = None/Minimal, 2 = Stressed, 3 = Crisis, 4 = Emergency, 5 = Catastrophe/Famine
-- period_kind: 'CS' (current situation), 'ML1' (near-term proj), 'ML2' (medium-term proj)
CREATE TABLE IF NOT EXISTS ipc_observations (
    id              BIGSERIAL PRIMARY KEY,
    region_id       INT REFERENCES regions(id),
    period_kind     VARCHAR(8)  NOT NULL,
    period_start    DATE        NOT NULL,
    period_end      DATE,
    ipc_phase       SMALLINT    NOT NULL CHECK (ipc_phase BETWEEN 1 AND 5),
    source          VARCHAR(32) DEFAULT 'fewsnet',
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (region_id, period_kind, period_start)
);
CREATE INDEX IF NOT EXISTS ipc_obs_region_idx ON ipc_observations (region_id, period_start DESC);
CREATE INDEX IF NOT EXISTS ipc_obs_phase_idx  ON ipc_observations (ipc_phase, period_start DESC);
