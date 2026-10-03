from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (ROOT / "docker-compose.prod.yml").is_file(),
    reason="deployment files are not mounted here",
)

COMPOSE_FILES = ("docker-compose.prod.yml", "docker-compose.yml")


def _services(name: str) -> dict:
    return yaml.safe_load((ROOT / name).read_text())["services"]


def _text(name: str) -> str:
    return (ROOT / name).read_text()


# ---------- backups ----------


def test_backup_stages_on_the_archive_disk():
    text = _text("scripts/backup.sh")
    assert "$(mktemp -d)" not in text
    assert 'WORK="$(mktemp -d -p "$dir" .rengine-stage.XXXXXX)"' in text
    assert 'stage "$DEST"' in text
    assert 'stage "$(dirname "$archive")"' in text


def test_restore_migrates_the_restored_database():
    restore = _text("scripts/backup.sh").split("\nrestore() {", 1)[1]
    assert restore.index("pg_restore") < restore.index("migrate 2>&1")
    assert restore.index("migrate 2>&1") < restore.index(
        'docker compose up -d "${SERVICES[@]}"'
    )


def test_snapshot_holds_the_database_and_the_key():
    text = _text("scripts/backup.sh")
    assert "snapshot) dump db ;;" in text
    assert "local members=(db.dump env)" in text
    assert '[ "$scope" = db ] || ask_passphrase' in text


# ---------- release images ----------


def _workflow(name: str) -> dict:
    return yaml.safe_load(_text(f".github/workflows/{name}"))


def test_images_are_built_from_the_tag_never_from_the_release():
    workflow = _workflow("build.yml")
    # PyYAML reads the key `on` as True
    triggers = workflow[True]
    assert set(triggers) == {"push"}
    assert triggers["push"]["tags"] == ["v*"]
    assert workflow["jobs"]["publish"]["needs"] == "build"
    assert workflow["jobs"]["release"]["needs"] == "publish"
    assert "--draft" in _text(".github/workflows/build.yml")


def test_every_image_is_built_for_both_architectures():
    matrix = _workflow("build.yml")["jobs"]["build"]["strategy"]["matrix"]
    assert matrix["image"] == ["api", "worker", "frontend"]
    assert matrix["arch"] == ["amd64", "arm64"]
    assert {row["arch"]: row["runner"] for row in matrix["include"]} == {
        "amd64": "ubuntu-24.04",
        "arm64": "ubuntu-24.04-arm",
    }


def test_master_moves_edge_and_a_release_moves_latest():
    text = _text(".github/workflows/build.yml")
    assert "type=edge,branch=master" in text
    assert "value=latest" not in text


def test_images_reach_both_registries():
    for job in ("build", "publish"):
        env = _workflow("build.yml")["jobs"][job]["env"]
        assert env["DOCKERHUB_REPO"].startswith("yogeshojha/rengine-")
        assert env["GHCR_REPO"].startswith("ghcr.io/yogeshojha/rengine-")


def test_release_images_take_their_version_from_the_tag():
    assert "RENGINE_VERSION=${{ steps.version.outputs.value }}" in _text(
        ".github/workflows/build.yml"
    )
    for dockerfile in ("api/Dockerfile", "worker/Dockerfile"):
        production = _text(dockerfile).split("AS production", 1)[1]
        assert 'ARG RENGINE_VERSION=""' in production, dockerfile
        assert "> /app/VERSION" in production, dockerfile


def test_installer_takes_both_architectures_and_an_image_prefix():
    text = _text("install.sh")
    assert "x86_64 | aarch64) ;;" in text
    assert "--image) IMAGE_PREFIX=" in text
    assert "docker compose pull || pull_failed" in text


# ---------- cache instance ----------


def test_cached_aggregates_live_on_an_evicting_instance():
    for compose in COMPOSE_FILES:
        services = _services(compose)
        cache = services["cache"]
        assert "--maxmemory-policy allkeys-lru" in cache["command"], compose
        assert '--save ""' in cache["command"], compose
        assert "--appendonly no" in cache["command"], compose
        assert "volumes" not in cache, compose
        assert "--maxmemory-policy noeviction" in services["redis"]["command"]
        assert "cache" in services["api"]["depends_on"], compose


def test_installer_and_env_example_name_the_cache_instance():
    assert "REDIS_CACHE_HOST=cache\n" in _text("install.sh")
    assert "REDIS_CACHE_MAXMEMORY=$CACHE_MAXMEMORY\n" in _text("install.sh")
    assert "REDIS_CACHE_HOST=cache\n" in _text(".env.example")


# ---------- database ----------


def test_database_absorbs_bulk_writes_and_stops_cleanly():
    for compose in COMPOSE_FILES:
        db = _services(compose)["db"]
        for setting in (
            "max_wal_size=${POSTGRES_MAX_WAL_SIZE:-2GB}",
            "checkpoint_timeout=15min",
            "wal_compression=lz4",
            "default_toast_compression=lz4",
        ):
            assert f"-c {setting}" in db["command"], (compose, setting)
        assert db["stop_grace_period"] == "2m", compose
        assert db["environment"]["POSTGRES_INITDB_ARGS"] == "--data-checksums"


def test_kernel_takes_a_worker_before_the_database():
    services = _services("docker-compose.prod.yml")
    assert "oom_score_adj" not in services["db"]
    assert services["worker-scans"]["oom_score_adj"] == 500
    for name in ("worker-default", "worker-control", "worker-beat", "ct-stream"):
        assert services[name]["oom_score_adj"] == 300, name


# ---------- updates ----------


def _services_list(text: str) -> str:
    return text.split("SERVICES=(", 1)[1].split(")", 1)[0]


def test_update_snapshots_and_quiesces_before_it_migrates():
    update = _text("deploy/rengine").split("\ncmd_update() {", 1)[1]
    update = update.split("\ncmd_scale() {", 1)[0]
    steps = [
        update.index(marker)
        for marker in (
            "-f docker-compose.prod.yml.new -f ports.yml pull",
            "scripts/backup.sh snapshot",
            'docker compose stop "${SERVICES[@]}"',
            "docker compose up -d --remove-orphans",
        )
    ]
    assert steps == sorted(steps)
    assert "--no-backup) backup=0 ;;" in update


def test_update_and_restore_stop_the_same_services():
    assert _services_list(_text("deploy/rengine")) == _services_list(
        _text("scripts/backup.sh")
    )
    assert _services_list(_text("deploy/rengine")) in _text("install.sh").replace(
        " \\\n   ", ""
    )


def test_installer_quiesces_an_upgrade_alone():
    text = _text("install.sh")
    assert '[ "$UPGRADE" -eq 1 ] && quiesce' in text
    assert (
        'if [ "$BUILD" -eq 1 ] || [ "$IMAGE_TAG" != "$before" ]; then UPGRADE=1; fi'
        in text
    )
    assert "--no-backup) NO_BACKUP=1 ;;" in text


# ---------- worker health ----------


def test_worker_healthcheck_reads_the_heartbeat_file():
    from shared.definitions.workers import HEARTBEAT_PATH  # noqa: PLC0415

    for compose in COMPOSE_FILES:
        services = _services(compose)
        for name in ("worker-default", "worker-scans", "worker-control"):
            assert services[name]["healthcheck"]["test"] == [
                "CMD-SHELL",
                f"find {HEARTBEAT_PATH} -mmin -2 | grep -q .",
            ], (compose, name)
        assert "inspect ping" not in _text(compose)


def test_workers_start_without_mingle_and_gossip():
    for compose in COMPOSE_FILES:
        services = _services(compose)
        for name in ("worker-default", "worker-scans", "worker-control"):
            command = services[name]["command"]
            assert "--without-mingle" in command, (compose, name)
            assert "--without-gossip" in command, (compose, name)
