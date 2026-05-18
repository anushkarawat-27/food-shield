-- Per-region crop portfolio. `share` is fraction of agricultural production
-- attributable to this crop in the region (sums to ~1.0 per region).
CREATE TABLE IF NOT EXISTS region_crops (
    region_id    INT REFERENCES regions(id),
    crop         VARCHAR(32),
    share        REAL NOT NULL,
    PRIMARY KEY (region_id, crop)
);
CREATE INDEX IF NOT EXISTS region_crops_crop_idx ON region_crops (crop);
