// Drives every result table's filter toolbar in a running instance over the DevTools protocol.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const PORT = Number(process.env.E2E_PORT ?? 9333);
const BASE = process.env.RENGINE_URL ?? 'http://127.0.0.1:5173';
const SCAN = process.argv[2];
const ONLY = process.argv[3] ? process.argv[3].split(',') : null;
const S = mkdtempSync(join(tmpdir(), 'rengine-e2e-'));
const [USER, PASS] = [process.env.RENGINE_USER, process.env.RENGINE_PASSWORD];
if ((!SCAN && !process.env.E2E_SURFACE) || !USER || !PASS) {
	console.error('usage: RENGINE_USER=… RENGINE_PASSWORD=… node scripts/e2e-filter-toolbar.mjs <scan id> [tabs]');
	process.exit(2);
}
const CHROME = process.env.CHROME ?? 'chromium';

const chrome = spawn(CHROME, [
	'--headless=new', `--remote-debugging-port=${PORT}`, '--no-sandbox', '--disable-gpu',
	'--window-size=1680,1000', `--user-data-dir=${S}/chrome-profile`, 'about:blank'
], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let version;
for (let i = 0; i < 50; i++) {
	try { version = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); break; } catch { await sleep(200); }
}
const ws = new WebSocket(version.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = new Map(); const events = [];
ws.onmessage = (m) => {
	const msg = JSON.parse(m.data);
	if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); } else events.push(msg);
};
const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
	const i = ++id; pending.set(i, (m) => (m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result)));
	ws.send(JSON.stringify({ id: i, method, params, sessionId }));
});
const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
const call = (m, p) => send(m, p, sessionId);
await call('Page.enable'); await call('Runtime.enable');
await call('Emulation.setDeviceMetricsOverride', { width: 1680, height: 1000, deviceScaleFactor: 1, mobile: false });
const evaluate = async (expression) => {
	const r = await call('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
	if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
	return r.result.value;
};
const HELPERS = `
window.__vis = (sel, root) => [...(root || document).querySelectorAll(sel)].filter(e => e.getClientRects().length > 0);
window.__text = (el) => (el?.textContent || '').replace(/\\s+/g, ' ').trim();
window.__rect = (el) => { const r = el.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; };
window.__group = (heading) => [...document.querySelectorAll('[data-slot="command-group"]')].find(g => __text(g.firstElementChild) === heading && g.getClientRects().length);
window.__count = () => {
	const input = __vis('input[aria-label^="Search"]')[0]; if (!input) return null;
	const top = input.getBoundingClientRect().top;
	const span = __vis('span').find(s => Math.abs(s.getBoundingClientRect().top - top) < 30 && /^\\d[\\d,]*\\+? [A-Za-z ]+$/.test(__text(s)));
	return span ? Number(__text(span).replace(/[^\\d]/g, '')) : null;
};
`;
async function click(expr) {
	const pos = await evaluate(`(() => { const el = (${expr}); if (!el) return null; el.scrollIntoView({ block: 'center' }); return __rect(el); })()`);
	if (!pos) throw new Error(`nothing to click for ${expr}`);
	await call('Input.dispatchMouseEvent', { type: 'mouseMoved', x: pos.x, y: pos.y });
	await call('Input.dispatchMouseEvent', { type: 'mousePressed', x: pos.x, y: pos.y, button: 'left', clickCount: 1 });
	await call('Input.dispatchMouseEvent', { type: 'mouseReleased', x: pos.x, y: pos.y, button: 'left', clickCount: 1 });
	await sleep(250);
}
async function clickUntil(expr, cond, attempts = 3) {
	for (let i = 0; i < attempts; i++) {
		await click(expr);
		try { return await until(cond, 2500); } catch { /* retry */ }
	}
	throw new Error(`no effect after ${attempts} clicks: ${expr.slice(0, 100)}`);
}
async function stableLabels() {
	let last = null;
	for (let i = 0; i < 20; i++) {
		const now = await evaluate(`__vis('button[aria-label^="Add filter "]').map(b => b.getAttribute('aria-label'))`);
		if (last && JSON.stringify(now) === JSON.stringify(last)) return now;
		last = now;
		await sleep(400);
	}
	return last ?? [];
}
async function key(k) {
	await call('Input.dispatchKeyEvent', { type: 'keyDown', key: k, code: k, windowsVirtualKeyCode: k === 'Escape' ? 27 : 0 });
	await call('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code: k, windowsVirtualKeyCode: k === 'Escape' ? 27 : 0 });
	await sleep(250);
}
async function until(expr, timeout = 12000) {
	const t0 = Date.now();
	while (Date.now() - t0 < timeout) {
		const v = await evaluate(expr);
		if (v) return v;
		await sleep(200);
	}
	throw new Error(`timed out: ${expr.slice(0, 120)}`);
}
const results = [];
function pass(tab, step, note = '') { results.push(['PASS', tab, step, note]); console.log(`PASS ${tab} · ${step} ${note}`); }
function fail(tab, step, note = '') { results.push(['FAIL', tab, step, note]); console.log(`FAIL ${tab} · ${step} ${note}`); }
async function step(tab, name, fn) {
	try { const note = await fn(); pass(tab, name, note ?? ''); } catch (e) {
		fail(tab, name, e.message);
		const shot = await call('Page.captureScreenshot', { format: 'png' });
		const file = join(S, `fail-${tab}-${name.replace(/\W+/g, '-')}.png`);
		writeFileSync(file, Buffer.from(shot.data, 'base64'));
		console.log(`  screenshot ${file}`);
	}
}
async function load(path) {
	await call('Page.navigate', { url: `${BASE}${path}` });
	await sleep(800);
	await until(`document.readyState === 'complete' && !document.body.innerText.includes('Loading…')`, 60000);
	await evaluate(HELPERS);
	try { await until(`__vis('[data-slot="skeleton"]').length === 0`, 20000); } catch { console.log('note: skeletons still visible after 20s'); }
	await sleep(600);
}

await call('Page.navigate', { url: `${BASE}/login` }); await sleep(800);
await evaluate(`localStorage.setItem('mode-watcher-mode', 'light'); 'ok'`);
const login = await evaluate(`fetch('/api/v1/auth/login',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({username:${JSON.stringify(USER)},password:${JSON.stringify(PASS)}})}).then(r=>r.status)`);
if (login !== 200) throw new Error(`login ${login}`);

const SURFACE = Boolean(process.env.E2E_SURFACE);
const pageFor = (tab, extra) => (SURFACE ? `/surface/${tab}${extra ? `?${extra.slice(1)}` : ''}` : `/scans/${SCAN}?tab=${tab}${extra}`);
const TABS = [
	['vulnerabilities', '&vuln_view=findings'], ['web-assets', ''], ['endpoints', ''], ['services', ''],
	['ips', ''], ['software', ''], ['secrets', ''], ['interesting', '']
].filter(([t]) => (!ONLY || ONLY.includes(t)) && !(SURFACE && t === 'interesting'));

for (const [tab, extra] of TABS) {
	await load(pageFor(tab, extra));
	const notScanned = await evaluate(`/\\bNot scanned\\b/.test(document.body.innerText) && __vis('button[aria-label="Filter"],button[aria-label^="Filter, "]').length === 0`);
	if (notScanned) { pass(tab, 'not scanned on this run', 'skipped'); events.length = 0; continue; }
	await step(tab, 'toolbar present', async () => {
		await until(`__vis('button[aria-label="Filter"],button[aria-label^="Filter, "]').length > 0`);
		const toolbars = await evaluate(`__vis('button[aria-label="Filter"],button[aria-label^="Filter, "]').length`);
		if (toolbars !== 1) throw new Error(`${toolbars} visible Filter buttons`);
	});
	if (tab !== 'interesting') {
		try { await until(`__vis('button[aria-label^="Add filter "]').length > 0`, 10000); } catch { /* reported below */ }
		try { await until(`__vis('button[aria-label^="Add filter "]').some(b => / rows$/.test(b.getAttribute('aria-label')))`, 6000); } catch { /* uncounted is allowed */ }
	}
	const suggestions = await stableLabels();
	const parsed = suggestions.map((l) => { const m = /^Add filter (.+?)(?:, (\d[\d,]*)\+? rows)?$/.exec(l); return m ? { query: m[1], count: m[2] ? Number(m[2].replace(/,/g, '')) : null } : null; }).filter(Boolean);
	await step(tab, 'suggestions offered', async () => {
		if (tab === 'interesting') return 'none expected';
		if (!parsed.length) throw new Error('no suggestion chips');
		return `${parsed.length}: ${parsed.map((p) => `${p.query}${p.count != null ? ` ${p.count}` : ''}`).join(' | ')}`;
	});
	const counted = parsed.find((p) => p.count != null);
	if (counted) {
		await step(tab, 'suggestion count is a promise', async () => {
			await clickUntil(`__vis('button[aria-label^="Add filter ${counted.query.replace(/"/g, '\\"')}"]')[0]`, `(__vis('input[aria-label^="Search"]')[0]?.value || '').includes(${JSON.stringify(counted.query)})`);
			const shown = await until(`__count()`, 15000);
			if (shown !== counted.count) throw new Error(`chip said ${counted.count}, table shows ${shown}`);
			await until(`__vis('[role=group][aria-label="Filter ${counted.query.replace(/"/g, '\\"')}"]').length > 0`);
			return `${counted.query} → ${shown}`;
		});
		await step(tab, 'second suggestions stay exact under the search', async () => {
			try { await until(`__vis('button[aria-label^="Add filter "]').some(b => / rows$/.test(b.getAttribute('aria-label')))`, 8000); } catch { /* none counted */ }
			const next = await stableLabels();
			const withCount = next.map((l) => /^Add filter (.+?), (\d[\d,]*)\+? rows$/.exec(l)).filter(Boolean);
			if (!withCount.length) return `no counted follow-up (${next.length} offered)`;
			const [, q, n] = withCount[0];
			await clickUntil(`__vis('button[aria-label^="Add filter ${q.replace(/"/g, '\\"')}"]')[0]`, `(__vis('input[aria-label^="Search"]')[0]?.value || '').includes(${JSON.stringify(q)})`);
			const shown = await until(`__count()`, 15000);
			if (shown !== Number(n.replace(/,/g, ''))) throw new Error(`${q}: chip said ${n}, table shows ${shown}`);
			return `${q} → ${shown}`;
		});
		await step(tab, 'clear removes chips and search', async () => {
			await click(`__vis('button[aria-label="Clear all filters"]')[0]`);
			await until(`(__vis('input[aria-label^="Search"]')[0]?.value || '') === '' && __vis('[role=group][aria-label^="Filter "]').length === 0`);
		});
	}
	await step(tab, 'facet picker writes a chip', async () => {
		await click(`__vis('button[aria-label="Filter"],button[aria-label^="Filter, "]')[0]`);
		await until(`__vis('[role=option]').length > 0`);
		const hasFacets = await evaluate(`Boolean(__group('Filters'))`);
		if (!hasFacets) { await key('Escape'); return 'no facets on this table'; }
		const facetLabel = await evaluate(`__text(__group('Filters').querySelector('[role=option]'))`);
		await click(`__group('Filters').querySelector('[role=option]')`);
		await until(`__vis('[role=option]').some(o => o.querySelector('.tabular-nums'))`);
		const optionLabel = await evaluate(`__text(__vis('[role=option]').find(o => o.querySelector('.tabular-nums')))`);
		await click(`__vis('[role=option]').find(o => o.querySelector('.tabular-nums'))`);
		await until(`__vis('[role=group][aria-label^="Filter "]').length > 0`);
		await key('Escape');
		await until(`__vis('[role=option]').length === 0`);
		const label = await evaluate(`__vis('button[aria-label="Filter"],button[aria-label^="Filter, "]')[0].getAttribute('aria-label')`);
		if (!/1 active/.test(label)) throw new Error(`filter button reads "${label}"`);
		const chip = await evaluate(`__text(__vis('[role=group][aria-label^="Filter "]')[0])`);
		await click(`__vis('button[aria-label="Clear all filters"]')[0]`);
		await until(`__vis('[role=group][aria-label^="Filter "]').length === 0`);
		return `${facetLabel} › ${optionLabel} → chip "${chip}"`;
	});
	await step(tab, 'signal toggles into a chip', async () => {
		if (tab === 'interesting') return 'no signals';
		await click(`__vis('button[aria-label="Filter"],button[aria-label^="Filter, "]')[0]`);
		await until(`__vis('[role=option]').length > 0`);
		const hasSignals = await evaluate(`Boolean(__group('Signals'))`);
		if (!hasSignals) { await key('Escape'); throw new Error('no Signals group'); }
		const label = await evaluate(`__text(__group('Signals').querySelector('[role=option]')).replace(/\\s*\\d[\\d,]*$/, '')`);
		await click(`__group('Signals').querySelector('[role=option]')`);
		await until(`__vis('[role=group][aria-label="Filter ${'${label}'}"]').length > 0`.replace('${label}', label.replace(/"/g, '\\"')));
		await key('Escape');
		await click(`__vis('button[aria-label="Clear all filters"]')[0]`);
		await until(`__vis('[role=group][aria-label^="Filter "]').length === 0`);
		return label;
	});
	if (process.env.E2E_STRESS) {
		await step(tab, 'stress: three suggestions in a row stay exact', async () => {
			if (tab === 'interesting') return 'none expected';
			const applied = [];
			for (let i = 0; i < 3; i++) {
				try { await until(`__vis('button[aria-label^="Add filter "]').some(b => / rows$/.test(b.getAttribute('aria-label')))`, 8000); } catch { /* none counted */ }
				const labels = await stableLabels();
				const hit = labels.map((l) => /^Add filter (.+?), (\d[\d,]*)\+? rows$/.exec(l)).find(Boolean);
				if (!hit) break;
				const [, q, n] = hit;
				const t0 = Date.now();
				await clickUntil(`__vis('button[aria-label^="Add filter ${q.replace(/"/g, '\\"')}"]')[0]`, `(__vis('input[aria-label^="Search"]')[0]?.value || '').includes(${JSON.stringify(q)})`);
				const shown = await until(`__count()`, 20000);
				if (shown !== Number(n.replace(/,/g, ''))) throw new Error(`${q}: chip said ${n}, table shows ${shown}`);
				applied.push(`${q} → ${shown} in ${Date.now() - t0} ms`);
				try { await until(`__vis('button[aria-label^="Add filter "]').some(b => / rows$/.test(b.getAttribute('aria-label')))`, 6000); } catch { /* none left */ }
			}
			if (applied.length) {
				await clickUntil(`__vis('button[aria-label="Clear all filters"]')[0]`, `__vis('[role=group][aria-label^="Filter "]').length === 0`);
			}
			return applied.join(' | ') || 'no counted suggestion';
		});
		await step(tab, 'stress: every facet picks and every signal toggles', async () => {
			if (await evaluate(`__vis('button[aria-label="Clear all filters"]').length > 0`)) {
				await clickUntil(`__vis('button[aria-label="Clear all filters"]')[0]`, `__vis('[role=group][aria-label^="Filter "]').length === 0`);
			}
			await click(`__vis('button[aria-label="Filter"],button[aria-label^="Filter, "]')[0]`);
			await until(`__vis('[role=option]').length > 0`);
			const facetCount = await evaluate(`__group('Filters') ? __group('Filters').querySelectorAll('[role=option]').length : 0`);
			let picked = 0;
			for (let i = 0; i < facetCount; i++) {
				await clickUntil(`__group('Filters').querySelectorAll('[role=option]')[${i}]`, `__vis('[role=option]').some(o => o.textContent.includes('Filters'))`);
				const option = await evaluate(`Boolean(__vis('[role=option]').find(o => o.querySelector('.tabular-nums')))`);
				if (option) {
					picked += 1;
					await clickUntil(`__vis('[role=option]').find(o => o.querySelector('.tabular-nums'))`, `__vis('[role=group][aria-label^="Filter "]').length === ${picked}`);
				}
				await clickUntil(`__vis('[role=option]').find(o => o.textContent.includes('Filters'))`, `Boolean(__group('Filters'))`);
			}
			const signalCount = await evaluate(`__group('Signals') ? __group('Signals').querySelectorAll('[role=option]').length : 0`);
			const chipsBefore = await evaluate(`__vis('[role=group][aria-label^="Filter "]').length`);
			const closedAfter = [];
			for (let i = 0; i < signalCount; i++) {
				const label = await evaluate(`__text(__group('Signals').querySelectorAll('[role=option]')[${i}]).replace(/\\s*\\d[\\d,]*$/, '')`);
				const before = await evaluate(`__group('Signals').querySelectorAll('[role=option]')[${i}].querySelector('.bg-primary') !== null`);
				for (const want of [!before, before]) {
					await clickUntil(`__group('Signals').querySelectorAll('[role=option]')[${i}]`, `!__group('Signals') || (__group('Signals').querySelectorAll('[role=option]')[${i}].querySelector('.bg-primary') !== null) === ${want}`);
					if (!(await evaluate(`Boolean(__group('Signals'))`))) {
						closedAfter.push(label);
						await click(`__vis('button[aria-label="Filter"],button[aria-label^="Filter, "]')[0]`);
						await until(`Boolean(__group('Signals'))`);
					}
				}
			}
			if (closedAfter.length) throw new Error(`menu closed after toggling ${closedAfter.join(', ')}`);
			await until(`__vis('[role=group][aria-label^="Filter "]').length === ${'${chipsBefore}'}`.replace('${chipsBefore}', chipsBefore));
			await key('Escape');
			await until(`__vis('[role=option]').length === 0`);
			const label = await evaluate(`__vis('button[aria-label="Filter"],button[aria-label^="Filter, "]')[0].getAttribute('aria-label')`);
			if (picked && !label.includes(`${picked} active`)) throw new Error(`picked ${picked}, button reads "${label}"`);
			if (picked) {
				await click(`__vis('button[aria-label="Clear all filters"]')[0]`);
				await until(`__vis('[role=group][aria-label^="Filter "]').length === 0`);
			}
			return `${facetCount} facets, ${picked} picked, ${signalCount} signals toggled twice`;
		});
	}
	if (process.env.E2E_STRESS) {
		await step(tab, 'stress: suggestion count stays exact under a facet', async () => {
			if (tab === 'interesting') return 'none expected';
			await click(`__vis('button[aria-label="Filter"],button[aria-label^="Filter, "]')[0]`);
			await until(`__vis('[role=option]').length > 0`);
			if (!(await evaluate(`Boolean(__group('Filters'))`))) { await key('Escape'); return 'no facets on this table'; }
			await clickUntil(`__group('Filters').querySelector('[role=option]')`, `__vis('[role=option]').some(o => o.textContent.includes('Filters'))`);
			if (!(await evaluate(`Boolean(__vis('[role=option]').find(o => o.querySelector('.tabular-nums')))`))) { await key('Escape'); return 'no counted option'; }
			await clickUntil(`__vis('[role=option]').find(o => o.querySelector('.tabular-nums'))`, `__vis('[role=group][aria-label^="Filter "]').length === 1`);
			await key('Escape');
			await until(`__vis('[role=option]').length === 0`);
			try { await until(`__vis('button[aria-label^="Add filter "]').some(b => / rows$/.test(b.getAttribute('aria-label')))`, 10000); } catch { /* none counted */ }
			const labels = await stableLabels();
			const hit = labels.map((l) => /^Add filter (.+?), (\d[\d,]*)\+? rows$/.exec(l)).find(Boolean);
			if (!hit) {
				await clickUntil(`__vis('button[aria-label="Clear all filters"]')[0]`, `__vis('[role=group][aria-label^="Filter "]').length === 0`);
				return 'no counted suggestion under the facet';
			}
			const [, q, n] = hit;
			await clickUntil(`__vis('button[aria-label^="Add filter ${q.replace(/"/g, '\\"')}"]')[0]`, `(__vis('input[aria-label^="Search"]')[0]?.value || '').includes(${JSON.stringify(q)})`);
			const shown = await until(`__count()`, 20000);
			if (shown !== Number(n.replace(/,/g, ''))) throw new Error(`${q} under a facet: chip said ${n}, table shows ${shown}`);
			await clickUntil(`__vis('button[aria-label="Clear all filters"]')[0]`, `__vis('[role=group][aria-label^="Filter "]').length === 0`);
			return `${q} → ${shown}`;
		});
	}
	await step(tab, 'view and more menus open', async () => {
		if (tab === 'interesting') return 'sort only';
		await click(`__vis('button[aria-label="View"],button[aria-label^="View, "]')[0]`);
		try { await until(`__vis('[role=menuitemradio],[role=menuitemcheckbox]').length > 0`, 3000); } catch {
			await click(`__vis('button[aria-label="View"],button[aria-label^="View, "]')[0]`);
			await until(`__vis('[role=menuitemradio],[role=menuitemcheckbox]').length > 0`);
		}
		await key('Escape');
		await until(`__vis('[role=menuitemradio],[role=menuitemcheckbox]').length === 0`);
		await click(`__vis('button[aria-label="More"]')[0]`);
		await until(`__vis('[role=menuitem]').some(m => /Export/.test(__text(m))) && __vis('[role=menuitem]').some(m => /Refresh/.test(__text(m)))`);
		await key('Escape');
	});
	if (tab === 'vulnerabilities') {
		await step(tab, 'summary severity chip writes the same chip', async () => {
			await click(`__vis('button[aria-label^="Critical:"]')[0]`);
			await until(`__vis('[role=group][aria-label="Filter Severity"]').length > 0`);
			const chip = await evaluate(`__text(__vis('[role=group][aria-label="Filter Severity"]')[0])`);
			await click(`__vis('button[aria-label="Clear all filters"]')[0]`);
			await until(`__vis('[role=group][aria-label^="Filter "]').length === 0`);
			return chip;
		});
		await step(tab, 'timeline keeps its own controls out of the toolbar', async () => {
			if (SURFACE) return 'no timeline across targets';
			await load(`/scans/${SCAN}?tab=vulnerabilities&vuln_view=timeline`);
			await until(`__vis('[aria-label="Scans shown"]').length > 0 && __vis('[aria-label="Rows"]').length > 0`);
			const filterTop = await evaluate(`__vis('button[aria-label="Filter"],button[aria-label^="Filter, "]')[0].getBoundingClientRect().top`);
			const windowTop = await evaluate(`__vis('[aria-label="Scans shown"]')[0].getBoundingClientRect().top`);
			if (!(windowTop > filterTop + 20)) throw new Error('window control sits in the toolbar row');
		});
	}
	const errors = events.filter((e) => e.method === 'Runtime.exceptionThrown').map((e) => e.params.exceptionDetails.exception?.description ?? e.params.exceptionDetails.text);
	await step(tab, 'no uncaught errors', async () => { if (errors.length) throw new Error(errors[0].slice(0, 200)); });
	events.length = 0;
}
const failed = results.filter((r) => r[0] === 'FAIL').length;
console.log(`\n${results.length - failed} passed, ${failed} failed`);
ws.close();
chrome.kill();
process.exit(failed ? 1 : 0);
