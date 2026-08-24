"""CLI smoke tests (pure paths) + migration file discipline."""

import json

from livelift.core.assigner.cli import main as schedule_main
from livelift.dbops.migrate import load_migrations


def test_schedule_cli_writes_valid_json(tmp_path, capsys):
    out = tmp_path / "schedule.json"
    rc = schedule_main(
        ["--duration", "90", "--block", "5", "--washout", "0", "--seed", "99",
         "--out", str(out)]
    )
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["seed"] == 99
    assert payload["n_measurement_blocks"] == payload["n_on"] + payload["n_off"]
    assert len(payload["blocks"]) >= payload["n_measurement_blocks"]
    # regenerating with the same seed gives the identical schedule (auditable)
    out2 = tmp_path / "schedule2.json"
    schedule_main(["--duration", "90", "--block", "5", "--washout", "0",
                   "--seed", "99", "--out", str(out2)])
    assert out.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")


def test_migrations_have_up_and_down_pairs():
    migrations = load_migrations()
    assert migrations, "no migrations found"
    versions = [m.version for m in migrations]
    assert versions == sorted(versions)
    for m in migrations:
        assert m.up_sql.strip()
        assert m.down_sql.strip()
    # every table created in up has a matching drop in down (E1-02 discipline)
    first = migrations[0]
    created = {
        line.split()[2].strip("(").lower()
        for line in first.up_sql.splitlines()
        if line.strip().upper().startswith("CREATE TABLE")
    }
    dropped = {
        line.split()[4].strip(";").lower()
        for line in first.down_sql.splitlines()
        if line.strip().upper().startswith("DROP TABLE IF EXISTS")
    }
    assert created <= dropped, f"missing drops for: {created - dropped}"
