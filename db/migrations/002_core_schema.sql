-- Admin-level regions (country + admin-1). Polygons from GADM/Natural Earth.
CREATE TABLE IF NOT EXISTS regions (
    id              SERIAL PRIMARY KEY,
    iso3            VARCHAR(3)  NOT NULL,
    admin_level     SMALLINT    NOT NULL,            -- 0 = country, 1 = state/province
    name            TEXT        NOT NULL,
    parent_id       INT         REFERENCES regions(id),
    geom            geometry(MultiPolygon, 4326) NOT NULL,
    centroid        geometry(Point, 4326),
    population      BIGINT,
    poverty_pct     REAL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS regions_geom_idx ON regions USING GIST (geom);
CREATE INDEX IF NOT EXISTS regions_iso3_idx ON regions (iso3);

-- Disruptor event types as enum-style lookup
CREATE TABLE IF NOT EXISTS disruptor_types (
    code        VARCHAR(16) PRIMARY KEY,
    label       TEXT NOT NULL
);
INSERT INTO disruptor_types (code, label) VALUES
    ('drought',  'Drought'),
    ('flood',    'Flooding'),
    ('heat',     'Extreme heat'),
    ('pest',     'Pest swarm'),
    ('frost',    'Frost')
ON CONFLICT DO NOTHING;

-- Raw disruptor events ingested from external feeds. Time-series via Timescale.
CREATE TABLE IF NOT EXISTS disruptor_events (
    id              BIGSERIAL,
    source          VARCHAR(32) NOT NULL,         -- 'firms','gdacs','fewsnet','giews'
    source_event_id TEXT,
    disruptor_type  VARCHAR(16) REFERENCES disruptor_types(code),
    severity        REAL,                          -- 0..1 normalized
    geom            geometry(Geometry, 4326) NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ,
    raw             JSONB,
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, started_at)
);
CREATE INDEX IF NOT EXISTS disruptor_events_geom_idx ON disruptor_events USING GIST (geom);
CREATE INDEX IF NOT EXISTS disruptor_events_type_idx ON disruptor_events (disruptor_type, started_at DESC);
SELECT create_hypertable('disruptor_events', 'started_at', if_not_exists => TRUE);

-- Crop calendar: per region + crop, planting/harvest windows
CREATE TABLE IF NOT EXISTS crop_calendar (
    region_id    INT REFERENCES regions(id),
    crop         VARCHAR(32),
    plant_start  SMALLINT,    -- day-of-year
    plant_end    SMALLINT,
    harvest_start SMALLINT,
    harvest_end  SMALLINT,
    PRIMARY KEY (region_id, crop)
);

-- Yield baselines (avg over historical window)
CREATE TABLE IF NOT EXISTS yield_baseline (
    region_id    INT REFERENCES regions(id),
    crop         VARCHAR(32),
    year         SMALLINT,
    yield_tpha   REAL,        -- tonnes per hectare
    PRIMARY KEY (region_id, crop, year)
);

-- Food price baselines (FAO GIEWS)
CREATE TABLE IF NOT EXISTS food_price_baseline (
    region_id    INT REFERENCES regions(id),
    commodity    VARCHAR(64),
    observed_at  DATE,
    price_usd    REAL,
    PRIMARY KEY (region_id, commodity, observed_at)
);

-- Cached projections
CREATE TABLE IF NOT EXISTS projections (
    id              BIGSERIAL PRIMARY KEY,
    region_id       INT REFERENCES regions(id),
    horizon_months  SMALLINT,
    ipc_phase       SMALLINT,    -- 1..5 IPC classification
    ci_low          REAL,
    ci_high         REAL,
    scenario_hash   VARCHAR(64),
    generated_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS projections_region_idx ON projections (region_id, horizon_months);
