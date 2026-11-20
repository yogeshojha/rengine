import datetime
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (ROOT / "docker-compose.prod.yml").is_file(),
    reason="deployment files are not mounted here",
)

MODES = ("domain", "ip", "local", "cert")
TLS_LINE = "\ttls /etc/caddy/tls/cert.pem /etc/caddy/tls/key.pem\n"
HSTS = 'header Strict-Transport-Security "max-age=31536000"'
RECREATE = "docker compose up -d --force-recreate --no-deps caddy"
BASH = shutil.which("bash") or "/bin/bash"


def _text(name: str) -> str:
    return (ROOT / name).read_text()


def _function(text: str, name: str) -> str:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"{name}() {{"))
    if lines[start].rstrip().endswith("}"):
        return lines[start] + "\n"
    body, heredoc = [], None
    for line in lines[start:]:
        body.append(line)
        if heredoc:
            heredoc = None if line == heredoc else heredoc
            continue
        opened = re.search(r"<<'?(\w+)'?", line)
        if opened:
            heredoc = opened.group(1)
        elif line == "}":
            break
    return "\n".join(body) + "\n"


def _installer(*names: str) -> str:
    text = _text("install.sh")
    return "".join(_function(text, name) for name in names)


def _bash(script: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        [BASH, "-c", "set -eo pipefail\n" + script],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _sandbox(tmp_path: Path, script: str, *names: str) -> subprocess.CompletedProcess:
    prelude = _installer("die", "env_get", "published_port", "write_private", *names)
    return _bash(f'{prelude}\nRENGINE_HOME="{tmp_path}"\n{script}', tmp_path)


def _caddyfile(tmp_path: Path, host: str, port: str) -> str:
    done = _sandbox(
        tmp_path,
        f"MODE=cert SERVER_HOST={host} UI_PORT={port} ACME_EMAIL=ops@example.com\n"
        "write_caddyfile",
        "valid_ipv4",
        "write_caddyfile",
    )
    assert done.returncode == 0, done.stderr
    return (tmp_path / "Caddyfile").read_text()


# ---------- the stored mode ----------


@pytest.mark.parametrize("mode", MODES)
def test_env_records_the_mode(tmp_path, mode):
    done = _sandbox(tmp_path, f"MODE={mode} BUILD=0\nwrite_env", "write_env")
    assert done.returncode == 0, done.stderr
    assert f"\nTLS_MODE={mode}\n" in (tmp_path / ".env").read_text()


def _kept(tmp_path: Path, env: str, ports: str) -> list[str]:
    (tmp_path / ".env").write_text(env)
    (tmp_path / "ports.yml").write_text(ports)
    done = _sandbox(
        tmp_path,
        'kept_reachability\necho "$MODE $SERVER_HOST $UI_PORT"',
        "env_set",
        "kept_reachability",
    )
    assert done.returncode == 0, done.stderr
    return done.stdout.split()


def test_kept_install_reads_the_stored_mode_before_the_guess(tmp_path):
    for host in ("", "rengine.corp"):
        assert _kept(
            tmp_path,
            f"PUBLIC_ORIGIN=https://rengine.corp:8443\nRENGINE_HOST={host}\nTLS_MODE=cert\n",
            'services:\n  caddy:\n    ports:\n      - "0.0.0.0:8443:443"\n',
        ) == ["cert", "rengine.corp", "8443"]


def test_kept_install_without_a_mode_records_the_guess(tmp_path):
    assert (
        _kept(
            tmp_path,
            "PUBLIC_ORIGIN=https://asm.example.com\nRENGINE_HOST=asm.example.com\n",
            'services:\n  caddy:\n    ports:\n      - "0.0.0.0:443:443"\n',
        )[0]
        == "domain"
    )
    assert "\nTLS_MODE=domain\n" in (tmp_path / ".env").read_text()


def test_reconfigure_appends_the_mode_to_an_older_env(tmp_path):
    (tmp_path / ".env").write_text("PUBLIC_ORIGIN=https://10.0.0.5\nRENGINE_HOST=\n")
    done = _sandbox(
        tmp_path,
        "MODE=cert PUBLIC_ORIGIN=https://rengine.corp RENGINE_HOST=\nupdate_env\nupdate_env",
        "update_env",
        "env_set",
    )
    assert done.returncode == 0, done.stderr
    env = (tmp_path / ".env").read_text()
    assert env.count("TLS_MODE=") == 1
    assert "\nTLS_MODE=cert\n" in env
    assert "PUBLIC_ORIGIN=https://rengine.corp\n" in env


# ---------- caddy ----------


def test_cert_caddyfile_for_a_hostname(tmp_path):
    caddyfile = _caddyfile(tmp_path, "rengine.corp", "443")
    site = caddyfile.split("https://rengine.corp {", 1)[1]
    assert TLS_LINE in site
    assert "\timport headers\n" in site
    assert HSTS in site
    assert "auto_https off" in caddyfile
    assert "email" not in caddyfile
    assert "tls internal" not in caddyfile
    assert "http://:80 {\n\timport headers\n\tredir https://{host}{uri}\n}" in caddyfile


def test_cert_caddyfile_for_an_address(tmp_path):
    caddyfile = _caddyfile(tmp_path, "10.0.0.5", "8443")
    assert TLS_LINE in caddyfile
    assert "default_sni 10.0.0.5" in caddyfile
    assert "Strict-Transport-Security" not in caddyfile
    assert "http://:80" not in caddyfile


@pytest.mark.parametrize(
    ("port", "published"),
    [
        ("443", ["0.0.0.0:443:443", "0.0.0.0:80:80"]),
        ("8443", ["0.0.0.0:8443:443"]),
    ],
)
def test_cert_mode_publishes_the_redirect_at_443_alone(tmp_path, port, published):
    done = _sandbox(tmp_path, f"MODE=cert UI_PORT={port}\nwrite_ports", "write_ports")
    assert done.returncode == 0, done.stderr
    ports = yaml.safe_load((tmp_path / "ports.yml").read_text())
    assert ports["services"]["caddy"]["ports"] == published


def test_compose_mounts_the_certificate_directory_read_only():
    caddy = yaml.safe_load(_text("docker-compose.prod.yml"))["services"]["caddy"]
    assert "./tls:/etc/caddy/tls:ro" in caddy["volumes"]
    assert caddy["cap_drop"] == ["ALL"]
    assert caddy["cap_add"] == ["NET_BIND_SERVICE"]


def test_every_install_path_creates_the_certificate_directory(tmp_path):
    text = _text("install.sh")
    done = _sandbox(tmp_path, "tls_dir\nstat -c %a tls", "tls_dir")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "700"
    assert "tls_dir" in _function(text, "write_files")
    main = _function(text, "main")
    keep = main.split("    kept_reachability\n", 1)[1].split("return 0", 1)[0]
    assert "tls_dir" in keep
    reconfigure = main.split("    check_certificate\n    install_certificate\n", 1)[1]
    assert reconfigure.index("tls_dir") < reconfigure.index("write_caddyfile")


def _docker_shim(tmp_path: Path, running: str) -> Path:
    shim = tmp_path / "shim"
    shim.mkdir()
    (shim / "docker").write_text(
        "#!/bin/sh\n"
        f'echo "$*" >>"{tmp_path}/docker.log"\n'
        f'case "$*" in "compose ps --status running -q caddy") echo "{running}" ;; esac\n'
    )
    (shim / "docker").chmod(0o755)
    return shim


@pytest.mark.parametrize(("running", "recreated"), [("c0ffee", True), ("", False)])
def test_recreate_caddy_restarts_a_running_caddy_alone(tmp_path, running, recreated):
    shim = _docker_shim(tmp_path, running)
    done = _sandbox(
        tmp_path, f'PATH="{shim}:$PATH" CLI=rengine\nrecreate_caddy', "recreate_caddy"
    )
    assert done.returncode == 0, done.stderr
    log = (tmp_path / "docker.log").read_text()
    assert (f"{RECREATE.removeprefix('docker ')}\n" in log) is recreated


def test_installer_recreates_caddy_after_rewriting_the_caddyfile():
    text = _text("install.sh")
    deploy = _function(text, "deploy")
    assert deploy.index("docker compose up -d --remove-orphans") < deploy.index(
        "recreate_caddy"
    )
    assert (
        'if [ "$KEEP_SETTINGS" -eq 1 ] || [ "$RECONFIGURE" -eq 1 ]; then recreate_caddy; fi'
        in deploy
    )
    assert RECREATE in _function(text, "recreate_caddy")
    main = _function(text, "main")
    keep = main.split("    kept_reachability\n", 1)[1].split("return 0", 1)[0]
    assert keep.index("write_caddyfile") < keep.index("recreate_caddy")
    assert keep.index("recreate_caddy") < keep.index('say "Configuration kept."')
    written = main.split('if [ "$NO_START" -eq 1 ]; then\n    [ "$RECONFIGURE"', 1)[1]
    assert written.index("recreate_caddy") < written.index("Configuration written")
    assert RECREATE in _function(_text("deploy/rengine"), "tls_set")


# ---------- one validation ----------


def test_the_certificate_check_lives_in_the_cli_alone():
    installer = _text("install.sh")
    assert "openssl x509" not in installer
    assert "checkend" not in installer
    assert (
        'bash "$TLS_CLI" tls check "$TLS_CERT" "$TLS_KEY" "$SERVER_HOST"' in installer
    )
    assert (
        'bash "$TLS_CLI" tls install "$TLS_CERT" "$TLS_KEY" "$RENGINE_HOME"'
        in installer
    )
    assert "-checkend 0" in _function(_text("deploy/rengine"), "cert_problem")


def test_the_certificate_is_copied_before_anything_is_written():
    main = _function(_text("install.sh"), "main")
    reconfigure = main.split(
        'if [ "$RECONFIGURE" -eq 1 ]; then\n    check_certificate\n', 1
    )[1]
    assert reconfigure.index("install_certificate") < reconfigure.index("update_env")
    fresh = main.split("    fetch_source\n", 1)[1]
    assert fresh.index("check_certificate") < fresh.index("install_certificate")
    assert fresh.index("install_certificate") < fresh.index("write_files")
    assert "tls_mode" not in _function(_text("deploy/rengine"), "tls_install")


def _pki(tmp_path: Path) -> dict[str, Path]:
    pytest.importorskip("cryptography")
    from cryptography import x509  # noqa: PLC0415
    from cryptography.hazmat.primitives import hashes, serialization  # noqa: PLC0415
    from cryptography.hazmat.primitives.asymmetric import ec, rsa  # noqa: PLC0415
    from cryptography.x509.oid import NameOID  # noqa: PLC0415

    now = datetime.datetime.now(datetime.UTC)
    ca_key, key, other = (ec.generate_private_key(ec.SECP256R1()) for _ in range(3))
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test CA")])

    k1 = ec.generate_private_key(ec.SECP256K1())

    def issue(name: str, start, end, subject_key=key) -> bytes:
        cert = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
            .issuer_name(ca_name)
            .public_key(subject_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(start)
            .not_valid_after(end)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(name)]), False)
            .sign(ca_key, hashes.SHA256())
        )
        return cert.public_bytes(serialization.Encoding.PEM)

    def private(value, encryption=None) -> bytes:
        return value.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            encryption or serialization.NoEncryption(),
        )

    week = now + datetime.timedelta(days=7)
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    files = {
        "cert": issue("rengine.corp", now, now + datetime.timedelta(days=30, hours=12)),
        "expired": issue(
            "rengine.corp",
            now - datetime.timedelta(days=60),
            now - datetime.timedelta(days=1),
        ),
        "other_name": issue("other.corp", now, now + datetime.timedelta(days=30)),
        "key": private(key),
        "other_key": private(other),
        "k1": issue("rengine.corp", now, week, k1),
        "k1_key": private(k1),
        "rsa": issue("rengine.corp", now, week, rsa_key),
        "rsa_encrypted": private(
            rsa_key, serialization.BestAvailableEncryption(b"secret")
        ),
    }
    files["combined"] = files["key"] + files["cert"]
    paths = {}
    for name, data in files.items():
        paths[name] = tmp_path / f"{name}.pem"
        paths[name].write_bytes(data)
    return paths


def _check(cert: Path, key: Path) -> subprocess.CompletedProcess:
    return _bash(
        f'bash "{ROOT}/deploy/rengine" tls check "{cert}" "{key}" rengine.corp', ROOT
    )


@pytest.mark.skipif(not shutil.which("openssl"), reason="openssl is not installed")
def test_tls_check_refuses_a_mismatched_key_and_an_expired_certificate(tmp_path):
    pki = _pki(tmp_path)
    good = _check(pki["cert"], pki["key"])
    assert good.returncode == 0, good.stderr
    assert "Certificate valid for 30 days." in good.stdout
    assert good.stderr == ""
    mismatched = _check(pki["cert"], pki["other_key"])
    assert mismatched.returncode == 1
    assert "the key does not match the certificate" in mismatched.stderr
    expired = _check(pki["expired"], pki["key"])
    assert expired.returncode == 1
    assert "the certificate expired on" in expired.stderr


@pytest.mark.skipif(not shutil.which("openssl"), reason="openssl is not installed")
@pytest.mark.parametrize(
    ("cert", "key", "reason"),
    [
        ("k1", "k1_key", "the certificate key type is not supported"),
        ("rsa", "rsa_encrypted", "rsa_encrypted.pem is encrypted"),
        ("combined", "key", "combined.pem holds a private key"),
    ],
)
def test_tls_check_refuses_what_caddy_cannot_load(tmp_path, cert, key, reason):
    pki = _pki(tmp_path)
    done = _check(pki[cert], pki[key])
    assert done.returncode == 1
    assert reason in done.stderr


@pytest.mark.skipif(not shutil.which("openssl"), reason="openssl is not installed")
def test_expiry_names_the_date_of_an_expired_certificate(tmp_path):
    pki = _pki(tmp_path)
    text = _text("deploy/rengine")
    prelude = "".join(
        _function(text, name) for name in ("cert_end", "cert_days", "cert_expiry")
    )
    good = _bash(f'{prelude}cert_expiry "{pki["cert"]}"', tmp_path)
    assert good.returncode == 0
    assert good.stdout == "Certificate expires in 30 days.\n"
    expired = _bash(f'{prelude}cert_expiry "{pki["expired"]}"', tmp_path)
    assert expired.returncode == 1
    assert re.fullmatch(
        r"Certificate expired on \w{3} +\d+ [\d:]+ \d{4} GMT\.\n", expired.stdout
    )


@pytest.mark.skipif(not shutil.which("openssl"), reason="openssl is not installed")
def test_tls_check_warns_when_the_certificate_does_not_name_the_host(tmp_path):
    pki = _pki(tmp_path)
    done = _check(pki["other_name"], pki["key"])
    assert done.returncode == 0
    assert "does not name rengine.corp" in done.stderr


def test_tls_set_refuses_outside_cert_mode(tmp_path):
    (tmp_path / "bin").mkdir()
    shutil.copy(ROOT / "deploy/rengine", tmp_path / "bin/rengine")
    (tmp_path / ".env").write_text("PUBLIC_ORIGIN=https://10.0.0.5\nTLS_MODE=ip\n")
    done = _bash("bash bin/rengine tls set cert.pem key.pem", tmp_path)
    assert done.returncode == 1
    assert "Run install.sh and choose Reconfigure" in done.stderr


CADDY_SHIM = """#!/bin/sh
echo "$*" >>"$LOG"
case "$*" in
  "image inspect"*) exit 0 ;;
  "run --rm -i"*) cat >/dev/null; exit 0 ;;
  "compose ps --status running -q caddy" | "compose ps -q caddy") echo c0ffee ;;
  "inspect -f"*) echo "$STATE" ;;
esac
"""


def _cert_install(
    tmp_path: Path, state: str
) -> tuple[subprocess.CompletedProcess, str]:
    pki = _pki(tmp_path)
    home = tmp_path / "home"
    (home / "bin").mkdir(parents=True)
    shutil.copy(ROOT / "deploy/rengine", home / "bin/rengine")
    shutil.copy(ROOT / "docker-compose.prod.yml", home)
    (home / ".env").write_text("PUBLIC_ORIGIN=https://rengine.corp\nTLS_MODE=cert\n")
    shim = tmp_path / "shim"
    shim.mkdir()
    (shim / "docker").write_text(CADDY_SHIM)
    (shim / "docker").chmod(0o755)
    log = tmp_path / "docker.log"
    done = _bash(
        f'PATH="{shim}:$PATH" LOG="{log}" STATE="{state}" '
        f'bash bin/rengine tls set "{pki["cert"]}" "{pki["key"]}"',
        home,
    )
    return done, log.read_text()


@pytest.mark.skipif(not shutil.which("openssl"), reason="openssl is not installed")
def test_tls_set_restores_the_previous_certificate_when_caddy_does_not_load(tmp_path):
    done, log = _cert_install(tmp_path, "false true 2")
    assert done.returncode == 1
    assert "The previous certificate is restored." in done.stderr
    assert "Caddy restarted" not in done.stdout
    assert "mv -f /tls/.cert.pem.prev /tls/cert.pem" in log
    assert log.count("compose up -d --force-recreate --no-deps caddy") == 2


@pytest.mark.skipif(not shutil.which("openssl"), reason="openssl is not installed")
def test_tls_set_recreates_caddy_alone_and_drops_the_previous_copy(tmp_path):
    done, log = _cert_install(tmp_path, "true false 0")
    assert done.returncode == 0, done.stderr
    assert "Certificate replaced. Caddy restarted." in done.stdout
    assert log.count("compose up -d --force-recreate --no-deps caddy") == 1
    assert "rm -f /tls/.cert.pem.prev /tls/.key.pem.prev" in log
    assert "/tls/.cert.pem.prev /tls/cert.pem" not in log


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (
            ["--local", "--tls-cert", "a.pem", "--tls-key", "b.pem"],
            "--tls-cert needs --domain <name> or --ip [address] to name the host",
        ),
        (
            ["--domain", "rengine.corp", "--tls-cert", "a.pem"],
            "--tls-cert needs --tls-key",
        ),
        (["--ip", "10.0.0.5", "--tls-key", "b.pem"], "--tls-key needs --tls-cert"),
    ],
)
def test_installer_refuses_certificate_flags_without_a_host(args, message):
    done = subprocess.run(  # noqa: S603
        [BASH, str(ROOT / "install.sh"), *args],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    assert done.returncode == 1
    assert message in done.stderr


# ---------- backups ----------


def test_backups_never_hold_the_certificate():
    text = _text("scripts/backup.sh")
    for members in re.findall(r"members=\(([^)]*)\)", text):
        assert "tls" not in members
    assert "VOLUMES=(vuln_templates wordlists report_fonts reports_out)" in text
    assert "key.pem" not in text
    assert "cert.pem" not in text
    assert 'say "The certificate is not in the archive. It stays in $HERE/tls."' in text


def test_uninstall_keeps_the_certificate():
    uninstall = _function(_text("deploy/rengine"), "cmd_uninstall")
    assert "Backups, .env and tls/ stay in %s." in uninstall
    assert "rm -" not in uninstall.replace('rm -f "$link"', "")
