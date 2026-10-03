import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (ROOT / "docker-compose.prod.yml").is_file(),
    reason="deployment files are not mounted here",
)

WORKERS = (
    "worker-default",
    "worker-scans",
    "worker-control",
    "worker-beat",
    "ct-stream",
)
BROWSERS = ("worker-default", "worker-scans")
API_ONLY = ("JWT_SECRET_KEY", "ADMIN_PASSWORD")
PROFILE = "seccomp=./deploy/seccomp-chromium.json"


def _services(name: str) -> dict:
    return yaml.safe_load((ROOT / name).read_text())["services"]


def _text(name: str) -> str:
    return (ROOT / name).read_text()


def _env_files(service: dict) -> list[str]:
    return [f if isinstance(f, str) else f["path"] for f in service.get("env_file", [])]


def _heredoc(text: str, opener: str) -> str:
    return text.split(opener, 1)[1].split("\nEOF", 1)[0]


# ---------- worker isolation ----------


def test_workers_drop_every_capability_but_raw_sockets():
    services = _services("docker-compose.prod.yml")
    for name in WORKERS:
        assert services[name]["cap_drop"] == ["ALL"], name
        assert services[name]["cap_add"] == ["NET_RAW"], name


def test_browser_workers_carry_the_chromium_profile():
    for compose in ("docker-compose.prod.yml", "docker-compose.yml"):
        services = _services(compose)
        for name in BROWSERS:
            assert services[name]["security_opt"] == [PROFILE], (compose, name)


def test_chromium_profile_opens_only_the_sandbox_syscalls():
    profile = json.loads(_text("deploy/seccomp-chromium.json"))
    assert profile["defaultAction"] == "SCMP_ACT_ERRNO"
    open_names = {
        name
        for rule in profile["syscalls"]
        if rule["action"] == "SCMP_ACT_ALLOW"
        and not {"args", "includes", "excludes"} & rule.keys()
        for name in rule["names"]
    }
    assert {"chroot", "clone", "unshare"} <= open_names
    assert not open_names & {
        "mount",
        "umount2",
        "setns",
        "bpf",
        "keyctl",
        "perf_event_open",
    }


def test_images_run_as_one_non_root_user():
    for dockerfile in ("worker/Dockerfile", "api/Dockerfile"):
        text = _text(dockerfile)
        production = text.split("AS production", 1)[1]
        assert "\nUSER rengine\n" in production, dockerfile
        assert "ARG RENGINE_UID=10001" in text, dockerfile


def test_volume_init_owns_every_writable_mount():
    services = _services("docker-compose.prod.yml")
    init = services["volume-init"]
    owned = {volume.split(":")[1] for volume in init["volumes"]}
    for target in owned:
        assert target in init["command"][0]
        assert target in _text("worker/Dockerfile").split("AS production", 1)[1]
    for name in (*WORKERS, "api"):
        mounts = {volume.split(":")[1] for volume in services[name].get("volumes", [])}
        assert mounts <= owned, name
        assert services[name]["depends_on"]["volume-init"] == {
            "condition": "service_completed_successfully"
        }, name


def test_tools_live_outside_root_home():
    text = _text("worker/Dockerfile")
    assert "/root/go/bin" not in text
    assert "COPY --chmod=755 worker/chrome.sh /usr/local/bin/chrome" in text


# ---------- api secrets ----------


def test_only_the_api_reads_api_env():
    services = _services("docker-compose.prod.yml")
    readers = {
        name for name, service in services.items() if "api.env" in _env_files(service)
    }
    assert readers == {"api"}


def test_prod_compose_blanks_api_secrets_outside_the_api():
    services = _services("docker-compose.prod.yml")
    for name in (*WORKERS, "channels", "migrate"):
        environment = services[name]["environment"]
        assert all(environment[key] == "" for key in API_ONLY), name


def test_dev_compose_blanks_api_secrets_outside_the_api():
    services = _services("docker-compose.yml")
    for name in (*WORKERS, "channels"):
        environment = services[name]["environment"]
        assert all(environment[key] == "" for key in API_ONLY), name


def test_installer_keeps_api_secrets_out_of_env():
    text = _text("install.sh")
    env = _heredoc(text, 'write_private "$RENGINE_HOME/.env.tmp" <<EOF')
    api = _heredoc(text, 'write_private "$RENGINE_HOME/api.env.tmp" <<EOF')
    for key in (
        "JWT_SECRET_KEY=",
        "ADMIN_PASSWORD=",
        "ADMIN_USERNAME=",
        "ADMIN_EMAIL=",
    ):
        assert key not in env, key
        assert key in api, key
    assert '[ -z "$JWT_SECRET_KEY" ] && JWT_SECRET_KEY="$(rand_hex 32)"' in text


def test_env_example_documents_jwt_secret_key():
    lines = _text(".env.example").splitlines()
    assert lines.index("JWT_SECRET_KEY=") > lines.index("SECRET_KEY=")


# ---------- published ports ----------


def test_installer_publishes_on_ipv4_and_loopback_only():
    published = re.findall(r'echo "      - \\"([^"\\]+)\\""', _text("install.sh"))
    assert published
    assert all(mapping.startswith(("0.0.0.0:", "127.0.0.1:")) for mapping in published)
    assert all(
        mapping.startswith("127.0.0.1:")
        for mapping in published
        if mapping.endswith(":8000")
    )


# ---------- installer credentials ----------


def test_installer_takes_no_password_as_an_argument():
    text = _text("install.sh")
    assert "--admin-password)" not in text
    assert "--admin-password-stdin) PASSWORD_STDIN=1" in text
    assert "MIN_PASSWORD_LENGTH=10" in text


def test_installer_writes_secrets_private_from_the_start():
    text = _text("install.sh")
    assert 'write_private() { (umask 077 && rm -f "$1" && cat >"$1"); }' in text
    assert 'cat >"$RENGINE_HOME/.env.tmp"' not in text


# ---------- backups ----------


def test_backup_encrypts_with_a_derived_key():
    text = _text("scripts/backup.sh")
    assert "CIPHER=(-aes-256-cbc -pbkdf2 -iter 600000 -md sha256)" in text
    assert 'say "The archive holds the instance key, SECRET_KEY."' in text


# ---------- caddy ----------


def test_caddy_sets_csp_only_when_the_upstream_did_not():
    text = _text("install.sh")
    assert "\t\t?Content-Security-Policy \"frame-ancestors 'none';" in text
    assert "\t\tContent-Security-Policy " not in text
