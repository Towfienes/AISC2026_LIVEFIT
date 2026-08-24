-- LiveLift schema v1 (project description §9.2 + research-synthesis additions:
-- compliance flags, server timestamps, shortlink/click_event for the
-- operational click definition, excluded_reason for flag-don't-edit policy).

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE product (
    product_id  text PRIMARY KEY,
    name        text NOT NULL,
    category    text,
    cost        numeric(12,0) NOT NULL DEFAULT 0,
    price       numeric(12,0) NOT NULL DEFAULT 0,
    stock       integer NOT NULL DEFAULT 0,
    margin      numeric(12,0) GENERATED ALWAYS AS (price - cost) STORED,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE live_session (
    session_id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    platform             text NOT NULL CHECK (platform IN ('youtube','facebook','tiktok','replay','sim')),
    title                text,
    mode                 text NOT NULL DEFAULT 'auto' CHECK (mode IN ('auto','suggest')),
    status               text NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','scheduled','live','ended')),
    planned_duration_min integer NOT NULL,
    start_ts             timestamptz,
    end_ts               timestamptz,
    host_id              text,
    ad_spend             numeric(12,0) DEFAULT 0,
    design               jsonb,          -- DesignParams + seed, persisted PRE-session
    runsheet             jsonb,
    created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE experiment_block (
    block_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      uuid NOT NULL REFERENCES live_session(session_id) ON DELETE CASCADE,
    block_index     integer NOT NULL,
    phase           text NOT NULL CHECK (phase IN ('early','mid','late')),
    assignment      text CHECK (assignment IN ('ON','OFF')),
    propensity      double precision,
    is_washout      boolean NOT NULL DEFAULT false,
    start_offset_s  integer NOT NULL,
    end_offset_s    integer NOT NULL,
    start_ts        timestamptz,
    end_ts          timestamptz,
    compliance_rate double precision,       -- share of block the assigned policy actually ran
    override_count  integer NOT NULL DEFAULT 0,
    excluded_reason text,                   -- flag, never edit experimental rows
    UNIQUE (session_id, block_index),
    CHECK (end_offset_s > start_offset_s),
    CHECK ((is_washout AND assignment IS NULL) OR (NOT is_washout AND assignment IS NOT NULL))
);

CREATE TABLE session_tick (
    session_id        uuid NOT NULL REFERENCES live_session(session_id) ON DELETE CASCADE,
    ts_bucket         timestamptz NOT NULL,
    viewers           double precision NOT NULL DEFAULT 0,
    comment_rate      double precision NOT NULL DEFAULT 0,
    like_rate         double precision NOT NULL DEFAULT 0,
    click_count       integer NOT NULL DEFAULT 0,
    pinned_product_id text REFERENCES product(product_id),
    PRIMARY KEY (session_id, ts_bucket)
);
SELECT create_hypertable('session_tick', 'ts_bucket', if_not_exists => TRUE, migrate_data => TRUE);

CREATE TABLE intervention_log (
    action_id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id                uuid NOT NULL REFERENCES live_session(session_id) ON DELETE CASCADE,
    block_id                  uuid REFERENCES experiment_block(block_id),
    ts                        timestamptz NOT NULL DEFAULT now(),  -- server-side, authoritative
    client_ts                 timestamptz,
    action_type               text NOT NULL,
    product_id                text REFERENCES product(product_id),
    source                    text NOT NULL CHECK (source IN ('model','human','holdback')),
    inner_propensity          double precision,
    candidates_json           jsonb,
    executed                  boolean NOT NULL DEFAULT true,
    override_reason           text,
    seconds_since_last_switch double precision
);
CREATE INDEX idx_intervention_session_ts ON intervention_log (session_id, ts);

CREATE TABLE comment_event (
    comment_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    uuid NOT NULL REFERENCES live_session(session_id) ON DELETE CASCADE,
    block_id      uuid REFERENCES experiment_block(block_id),
    ts            timestamptz NOT NULL,
    text_scrubbed text NOT NULL,             -- ONLY the scrubbed text ever reaches this table
    pii_kinds     text[] NOT NULL DEFAULT '{}',
    intent_label  text,
    sentiment     text
);
CREATE INDEX idx_comment_session_ts ON comment_event (session_id, ts);

CREATE TABLE shortlink (
    code       text PRIMARY KEY,
    product_id text NOT NULL REFERENCES product(product_id),
    session_id uuid REFERENCES live_session(session_id),
    target_url text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- The operational definition of the primary outcome: a click = one request to
-- the self-hosted redirect /r/{code} (research synthesis L5).
CREATE TABLE click_event (
    click_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id     uuid REFERENCES live_session(session_id) ON DELETE CASCADE,
    block_id       uuid REFERENCES experiment_block(block_id),
    ts             timestamptz NOT NULL DEFAULT now(),
    product_id     text REFERENCES product(product_id),
    shortlink_code text REFERENCES shortlink(code),
    dedup_hash     text        -- hash with per-session rotating salt (§11.2); dedup only
);
CREATE INDEX idx_click_session_ts ON click_event (session_id, ts);

CREATE TABLE order_event (
    order_id   text PRIMARY KEY,
    session_id uuid REFERENCES live_session(session_id),
    block_id   uuid REFERENCES experiment_block(block_id),
    ts         timestamptz NOT NULL,
    product_id text REFERENCES product(product_id),
    qty        integer NOT NULL DEFAULT 1,
    gross      numeric(12,0) NOT NULL DEFAULT 0,
    fees       numeric(12,0) NOT NULL DEFAULT 0,
    net_margin numeric(12,0)
);
CREATE INDEX idx_order_session_ts ON order_event (session_id, ts);

CREATE TABLE analysis_run (
    run_id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at         timestamptz NOT NULL DEFAULT now(),
    prereg_commit_hash text,
    estimator          text NOT NULL,
    outcome            text NOT NULL,
    estimate           double precision,
    ci_low             double precision,
    ci_high            double precision,
    p_value            double precision,
    n_blocks           integer,
    params             jsonb
);
