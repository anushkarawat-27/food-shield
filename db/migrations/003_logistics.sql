-- Food aid logistics: depots, ports, road network constraints, conflict overlays.
CREATE TABLE IF NOT EXISTS depots (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    geom            geometry(Point, 4326) NOT NULL,
    stock_tonnes    REAL DEFAULT 0,
    capacity_tonnes REAL
);

CREATE TABLE IF NOT EXISTS ports (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    iso3            VARCHAR(3),
    geom            geometry(Point, 4326) NOT NULL,
    throughput_tpd  REAL                          -- tonnes/day
);

CREATE TABLE IF NOT EXISTS routes (
    id              SERIAL PRIMARY KEY,
    from_node       TEXT,                          -- depot/port id encoded
    to_region_id    INT REFERENCES regions(id),
    distance_km     REAL,
    cost_usd_per_t  REAL,
    capacity_tpd    REAL
);

-- Conflict zones (ACLED-style)
CREATE TABLE IF NOT EXISTS conflict_zones (
    id              BIGSERIAL PRIMARY KEY,
    geom            geometry(Geometry, 4326) NOT NULL,
    intensity       REAL,                          -- 0..1
    observed_at     DATE,
    source          VARCHAR(32)
);
CREATE INDEX IF NOT EXISTS conflict_zones_geom_idx ON conflict_zones USING GIST (geom);

-- Saved scenarios (user-built)
CREATE TABLE IF NOT EXISTS scenarios (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT,
    payload         JSONB NOT NULL,                -- { region_id: { disruptor: severity } }
    created_by      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
