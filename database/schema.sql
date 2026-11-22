-- Skema database AGROHEAT (SQLite). Dibuat otomatis oleh db_manager.init_db().

CREATE TABLE IF NOT EXISTS batches (
    batch_id               TEXT PRIMARY KEY,
    material               TEXT NOT NULL,
    material_type          TEXT NOT NULL,
    volume_ml              REAL NOT NULL CHECK (volume_ml > 0),
    initial_temperature    REAL NOT NULL,
    target_temperature     REAL NOT NULL,
    heating_condition      TEXT NOT NULL,
    data_source            TEXT NOT NULL
        CHECK (data_source IN ('real_sensor','public_dataset','manual','simulation')),
    start_time             TEXT,
    end_time               TEXT,
    target_reached_seconds REAL,     -- elapsed saat pertama kali mencapai target
    actual_duration_seconds REAL,    -- elapsed terakhir saat sesi diakhiri
    status                 TEXT NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending','Heating','Target Reached','Completed','Cancelled')),
    notes                  TEXT DEFAULT '',
    created_at             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS readings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
    timestamp       TEXT NOT NULL,
    temperature_c   REAL,            -- NULL jika sensor tidak terbaca
    elapsed_seconds REAL NOT NULL,
    sensor_status   TEXT NOT NULL DEFAULT 'connected',
    data_source     TEXT NOT NULL
        CHECK (data_source IN ('real_sensor','public_dataset','manual','simulation')),
    received_at     TEXT NOT NULL    -- waktu data diterima laptop (jam laptop)
);
CREATE INDEX IF NOT EXISTS idx_readings_batch ON readings(batch_id, elapsed_seconds);

CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id    TEXT REFERENCES batches(batch_id) ON DELETE CASCADE,
    timestamp   TEXT NOT NULL,
    alert_type  TEXT NOT NULL,
    priority    TEXT NOT NULL CHECK (priority IN ('Critical','Warning','Info')),
    message     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'Active'
        CHECK (status IN ('Active','Acknowledged','Resolved'))
);

CREATE TABLE IF NOT EXISTS model_experiments (
    experiment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name        TEXT NOT NULL,
    training_date     TEXT NOT NULL,
    dataset_version   TEXT NOT NULL,
    train_batch_count INTEGER NOT NULL,
    test_batch_count  INTEGER NOT NULL,
    mae               REAL,
    rmse              REAL,
    notes             TEXT
);

CREATE TABLE IF NOT EXISTS system_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT
);
