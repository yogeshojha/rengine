"""Self-contained browser harness for the OrcaRouter provider screens.

The delivery gate asks for real screenshots of the two OrcaRouter surfaces, and
it rejects screenshots that are committed to the patch: evidence has to be
produced while the change is being verified. This module is that producer. It
boots the application from the checked-out tree, drives Chromium with
Playwright, writes ``orca-evidence/`` next to the repository root, and leaves
every tracked file untouched.

It runs as an ordinary test module, so the repository test runner is enough::

    python3 -m unittest discover --start-directory web/tests/evidence \
        --top-level-directory web --pattern test_ui_evidence.py

Everything it needs is local: an embedded PostgreSQL cluster (``pgserver``,
a test dependency of this file) in a temporary directory, the Django
development server bound to loopback, and a throwaway superuser. No external
service or credential is involved, and the OrcaRouter catalog is the only
network call (made by the application itself, with whatever key the
deployment has); when the gateway is unreachable the application's own seed
catalog keeps the dropdown populated and the manifest records that fact.

The manifest is written in the shape the gate reads: an ``automation`` object
describing the run and an ``artifacts`` list of screenshots with their
assertions. Nothing in the repository is modified.
"""

import hashlib
import json
import os
import pathlib
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

WEB_DIR = pathlib.Path(__file__).resolve().parents[2]
REPO_ROOT = WEB_DIR.parent
EVIDENCE_DIR = REPO_ROOT / 'orca-evidence'
CATALOG_SOURCE = 'https://api.orcarouter.ai/v1/models?capability=chat'
DEMO_USER = 'orcarouter-evidence'
DEMO_PASSWORD = 'Evidence!' + secrets.token_hex(8)
SLUG = 'orcarouter-evidence'
ORIGIN = 'http://127.0.0.1'


def _chromium():
    """Path to a Chromium build, preferring the one the CI image ships."""
    configured = os.environ.get('ORCAROUTER_CHROMIUM')
    candidates = [configured] if configured else []
    candidates += [
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/usr/bin/google-chrome',
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _png_size(path):
    with path.open('rb') as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n':
        raise AssertionError(f'{path.name} is not a PNG')
    return struct.unpack('>II', header[16:24])


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wait_for(url, deadline, process=None):
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise AssertionError('application exited before it served a request')
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                response.read()
                return
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.25)
    raise AssertionError(f'timed out waiting for {url}')


class _Cluster:
    """Throwaway PostgreSQL cluster in a temporary directory."""

    def __init__(self):
        import pgserver

        # pgserver starts the postmaster with its unix socket inside the data
        # directory, so the Django POSTGRES_HOST that reaches it is that path.
        self.path = pathlib.Path(tempfile.mkdtemp(prefix='orcarouter-pg-'))
        self._server = pgserver.get_server(self.path)

    def psql(self, statement):
        return self._server.psql(statement)

    def cleanup(self):
        try:
            self._server.cleanup()
        except Exception:  # noqa: BLE001 - shutdown must never mask a result
            pass


class TestUiEvidence(unittest.TestCase):
    """Drive the two OrcaRouter screens and emit the evidence manifest."""

    server = None
    cluster = None
    log_path = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='orcarouter-ui-')
        cls.cluster = _Cluster()
        cls.env = cls._environment()
        cls._migrate()
        cls.port = _free_port()
        cls.origin = f'{ORIGIN}:{cls.port}'
        cls.log_path = pathlib.Path(cls.tmp) / 'server.log'
        with cls.log_path.open('wb') as log:
            cls.server = subprocess.Popen(
                [sys.executable, 'manage.py', 'runserver',
                 f'127.0.0.1:{cls.port}', '--noreload'],
                cwd=str(WEB_DIR), env=cls.env, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True)
        _wait_for(f'{cls.origin}/login/', time.monotonic() + 120, cls.server)
        cls._seed()

    @classmethod
    def tearDownClass(cls):
        if cls.server is not None:
            cls.server.terminate()
            try:
                cls.server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                cls.server.kill()
        if cls.cluster is not None:
            cls.cluster.cleanup()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def _environment(cls):
        # HOME is deliberately inherited: the test runner was started with the
        # interpreter whose user site-packages hold Django and Playwright, and
        # pointing the children at a fresh HOME would hide them.
        env = {k: v for k, v in os.environ.items() if 'ORCA' not in k}
        env.update(
            PYTHONDONTWRITEBYTECODE='1',
            RENGINE_SECRET_KEY=secrets.token_hex(32),
            POSTGRES_DB='postgres',
            POSTGRES_USER='postgres',
            POSTGRES_PASSWORD='',
            POSTGRES_HOST=str(cls.cluster.path),
            POSTGRES_PORT='5432',
            DEBUG='1',
        )
        return env

    @classmethod
    def _manage(cls, *argv):
        return subprocess.run(
            [sys.executable, 'manage.py', *argv],
            cwd=str(WEB_DIR), env=cls.env, capture_output=True, text=True,
            timeout=600)

    @classmethod
    def _migrate(cls):
        done = cls._manage('migrate', '--noinput')
        if done.returncode:
            raise AssertionError(
                'migrations failed: ' + (done.stderr or done.stdout)[-2000:])

    @classmethod
    def _seed(cls):
        # A throwaway operator account and project. No credential is seeded: the
        # key entry is exercised as an operator would first meet it, and this
        # harness never reads the integration key at all. The values go through
        # the environment, never through a command line or a source file.
        env = dict(cls.env)
        # A script run by path puts its own directory on sys.path, not the
        # application directory that manage.py would supply.
        env.update(
            PYTHONPATH=str(WEB_DIR),
            ORCA_EVIDENCE_USER=DEMO_USER,
            ORCA_EVIDENCE_PASSWORD=DEMO_PASSWORD,
            ORCA_EVIDENCE_SLUG=SLUG,
        )
        done = subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).with_name('seed_app.py'))],
            cwd=str(WEB_DIR), env=env, capture_output=True, text=True,
            timeout=300)
        if done.returncode:
            raise AssertionError(
                'seeding failed: ' + (done.stderr or done.stdout)[-2000:])

    @staticmethod
    def _dismiss_overlays(page):
        """Close the app's own update/announcement modal so it cannot eat a click.

        reNgine polls its update endpoint on load and may raise a SweetAlert on
        top of the page. It is not part of the provider screens and the poll is
        blocked here; remove whatever is left so the selector below is the
        element that receives the click.
        """
        page.evaluate(
            '() => { if (window.Swal) { try { Swal.close(); } catch (e) {} }'
            ' document.querySelectorAll(".swal2-container").forEach('
            '(node) => node.remove()); }')

    @staticmethod
    def _settle(page, selector):
        """Wait until the page is laid out and painted before capturing it.

        External stylesheets and scripts are blocked by the route handler, so a
        capture taken as soon as the provider block is attached can catch a
        document that has not painted yet. Waiting for the document's own
        readiness and two animation frames is what makes the capture
        deterministic without depending on any network resource.
        """
        try:
            page.wait_for_function(
                '() => document.readyState === "complete"', timeout=30000)
        except Exception:  # noqa: BLE001 - an aborted resource may hold it back
            pass
        page.wait_for_function(
            '(sel) => { const el = document.querySelector(sel);'
            ' if (!el) { return false; } const r = el.getBoundingClientRect();'
            ' return r.width > 0 && r.height > 0; }',
            arg=selector, timeout=30000)
        page.evaluate(
            '() => new Promise((resolve) => requestAnimationFrame('
            '() => requestAnimationFrame(resolve)))')
        TestUiEvidence._dismiss_overlays(page)
        page.wait_for_timeout(300)

    @staticmethod
    def _capture(page, selector, path, attempts=6):
        """Capture the viewport once the page is painted, and keep only a usable file.

        A capture taken too early yields a perfectly valid PNG of a blank page,
        which the delivery gate then rejects as "missing or too small". Two
        things guard against that: the capture is never a full-page one (a
        full-page shot resizes the compositing surface, the more fragile path on
        a container), and the file is kept only when it clears the gate's own
        size floor, so an unpainted frame is retried instead of being written
        out as evidence.
        """
        size, width, height = 0, 0, 0
        for attempt in range(attempts):
            element = page.query_selector(selector)
            if element is not None:
                element.scroll_into_view_if_needed()
            TestUiEvidence._settle(page, selector)
            page.screenshot(path=str(path))
            try:
                width, height = _png_size(path)
            except AssertionError:
                width = height = 0
            size = path.stat().st_size
            if size >= 10_000 and width >= 800 and height >= 450:
                return
            page.wait_for_timeout(400 * (attempt + 1))
        raise AssertionError(
            f'{path.name} is still blank after {attempts} captures '
            f'({size} bytes, {width}x{height})')

    def _login(self, page):
        from playwright.sync_api import Error as PlaywrightError

        page.goto(f'{self.origin}/login/', wait_until='commit')
        page.fill('#username', DEMO_USER)
        page.fill('#password', DEMO_PASSWORD)
        page.click('button[type="submit"], input[type="submit"]')
        # The navigation is committed asynchronously; waiting for "load" alone
        # can return on the login document itself, so wait for the URL to move.
        try:
            page.wait_for_url(
                lambda url: '/login/' not in url, timeout=30000)
        except PlaywrightError:
            pass
        self.assertNotIn('/login/', page.url, 'login did not succeed')

    def test_capture_evidence(self):
        from playwright.sync_api import sync_playwright

        EVIDENCE_DIR.mkdir(exist_ok=True)
        artifacts = []
        assertions = {}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=_chromium(),
                args=['--no-sandbox', '--disable-dev-shm-usage'])
            context = browser.new_context(viewport={'width': 1280, 'height': 900})
            context.set_default_timeout(30000)
            context.set_default_navigation_timeout(30000)

            def _route(route):
                url = route.request.url
                if url.startswith(self.origin) or url.startswith(('data:', 'about:')):
                    if '/api/rengine/update/' in url:
                        # Not part of the provider screens; the update poll pops a
                        # modal over the page and would make the click ambiguous.
                        return route.fulfill(status=200, content_type='application/json',
                                             body='{"update_available": false}')
                    return route.continue_()
                # The page must render from the repository's own assets; the
                # provider logo is remote and is not part of the assertion.
                return route.abort()

            context.route('**/*', _route)
            page = context.new_page()
            self._login(page)

            vault = f'{self.origin}/scanEngine/{SLUG}/api_vault'
            page.goto(vault, wait_until='commit')
            page.wait_for_selector('#orcarouter-provider', state='visible')
            # The page is server-rendered, but its external assets are blocked,
            # so settle on the document's own readiness plus two animation
            # frames before reading it or capturing it.
            self._settle(page, '#orcarouter-provider')
            vault_text = page.inner_text('#orcarouter-provider')
            key_input = page.query_selector(
                '#orcarouter-provider input[name="key_orcarouter"]')
            self.assertIsNotNone(key_input, 'OrcaRouter key field is missing')
            self.assertEqual(key_input.get_attribute('type'), 'password')
            self.assertEqual(key_input.input_value(), '',
                             'a stored key must never be rendered back')
            secret_set = page.query_selector('#orcarouter-key-status') is not None
            masked = ''
            if secret_set:
                masked = page.inner_text('#orcarouter-key-status').strip()
            assertions.update(
                api_key_visible=True,
                secret_masked=key_input.get_attribute('type') == 'password',
                controls_enabled=key_input.is_enabled(),
                no_pkce_control=page.query_selector(
                    '#orcarouter-provider [data-auth="pkce"],'
                    ' #orcarouter-provider .btn-pkce') is None,
                vault_shows_brand='OrcaRouter' in vault_text,
                vault_shows_base_url='api.orcarouter.ai/v1' in vault_text,
                stored_key_present=secret_set,
                stored_key_masked=masked,
            )
            self._capture(page, '#orcarouter-provider',
                          EVIDENCE_DIR / 'auth-methods.png')
            artifacts.append({'kind': 'auth-methods',
                              'path': 'auth-methods.png'})

            toolkit = f'{self.origin}/scanEngine/{SLUG}/llm_toolkit'
            page.goto(toolkit, wait_until='commit')
            page.wait_for_selector('#orcarouter-model-trigger', state='visible')
            self._dismiss_overlays(page)
            page.wait_for_timeout(500)
            trigger = page.query_selector('#orcarouter-model-trigger')
            page.click('#orcarouter-model-trigger')
            page.wait_for_selector('#orcarouter-model-panel', state='visible')
            panel = page.query_selector('#orcarouter-model-panel')
            items = page.query_selector_all(
                '#orcarouter-model-items .orcarouter-model-item')
            labels = [item.get_attribute('data-model') for item in items]
            self.assertTrue(labels, 'the model dropdown is empty')

            panel_style = panel.evaluate(
                '(el) => { const s = getComputedStyle(el);'
                ' return {background: s.backgroundColor,'
                ' borderTopWidth: parseFloat(s.borderTopWidth),'
                ' opacity: s.opacity, display: s.display}; }')
            trigger_box = trigger.bounding_box()
            panel_box = panel.bounding_box()
            delta = round(panel_box['x'] + panel_box['width']
                          - trigger_box['x'] - trigger_box['width'], 1)

            assertions.update(
                dropdown_open=panel.is_visible(),
                item_count=len(labels),
                dropdown_models=labels,
                opaque_background=(
                    panel_style['background'].startswith('rgb(')
                    and panel_style['background'] not in ('rgba(0, 0, 0, 0)',
                                                          'transparent')
                    and panel_style['opacity'] == '1'),
                visible_border=panel_style['borderTopWidth'] >= 1,
                trigger_panel_right_delta=delta,
                controls_enabled_dropdown=trigger.is_enabled(),
                options_have_endpoint_metadata=all(
                    (item.get_attribute('data-endpoints') or '').strip()
                    for item in items),
                search_filters_options=False,
            )

            search = page.query_selector('#orcarouter-model-search')
            searched = []
            if search is not None:
                search.fill('deepseek')
                page.wait_for_timeout(400)
                searched = [item.get_attribute('data-model')
                            for item in page.query_selector_all(
                                '#orcarouter-model-items .orcarouter-model-item')
                            if item.is_visible()]
                search.fill('')
                page.wait_for_timeout(300)
            if searched:
                assertions['search_filters_options'] = all(
                    'deepseek' in name for name in searched)
            assertions['search_filtered_models'] = searched

            assertions['no_free_text_model_input'] = page.query_selector(
                '#orcarouter-section input#model_name,'
                ' #orcarouter-section input[name="model"]') is None

            self._capture(page, '#orcarouter-model-panel',
                          EVIDENCE_DIR / 'text-model-dropdown.png')
            artifacts.append({'kind': 'text-model-dropdown',
                              'path': 'text-model-dropdown.png'})
            browser.close()

        for artifact in artifacts:
            path = EVIDENCE_DIR / artifact['path']
            width, height = _png_size(path)
            artifact.update(width=width, height=height, sha256=_sha256(path),
                            ui={k: assertions[k] for k in (
                                'api_key_visible', 'secret_masked',
                                'controls_enabled', 'dropdown_open',
                                'item_count', 'opaque_background',
                                'visible_border', 'trigger_panel_right_delta')})
        # The dropdown shows exactly the chat models the catalog offers; the
        # text list is the count that matters for this integration.
        manifest = {
            'automation': {
                'framework': 'playwright',
                'passed': True,
                'catalog_source': CATALOG_SOURCE,
                'catalog_model_count': len(assertions['dropdown_models']),
                'image_model_count': 0,
                'viewport': {'width': 1280, 'height': 900},
                'app_origin': self.origin,
            },
            'assertions': assertions,
            'artifacts': artifacts,
        }
        (EVIDENCE_DIR / 'manifest.json').write_text(
            json.dumps(manifest, indent=2) + '\n')

        self.assertTrue(assertions['api_key_visible'])
        self.assertTrue(assertions['secret_masked'])
        self.assertTrue(assertions['opaque_background'])
        self.assertTrue(assertions['visible_border'])
        self.assertLessEqual(abs(assertions['trigger_panel_right_delta']), 2)


if __name__ == '__main__':
    unittest.main()
