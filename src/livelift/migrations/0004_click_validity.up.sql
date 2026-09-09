-- Valid-click flags for the primary outcome (gói Q1, 08/09).
--
-- IAB Click Measurement Guidelines (2009) + Fabijan et al. (KDD 2019, bot
-- filtering in online experiments): a click row is NEVER deleted — invalid
-- traffic is FLAGGED (flag-don't-drop) so raw and valid counts can both be
-- reported and any classification can be re-run (τ sensitivity, T+30'
-- reconciliation via livelift.core.click_validity.recount_click_validity).
--
-- is_valid        : the click counts toward the primary outcome (default true;
--                   legacy rows predate classification and stay valid).
-- invalid_reason  : one of 'givt_ua', 'prefetch', 'non_get', 'refractory',
--                   'volume_cap' — NULL when valid.
-- ua_class        : coarse user-agent class ('givt' / 'browser' / 'unknown');
--                   the raw user-agent string is deliberately NOT stored (§11.2).

ALTER TABLE click_event
    ADD COLUMN is_valid       boolean NOT NULL DEFAULT true,
    ADD COLUMN invalid_reason text,
    ADD COLUMN ua_class       text;
