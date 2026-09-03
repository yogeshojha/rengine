#!/usr/bin/env node
// Vendors Wappalyzer technology logos into static/tech-icons/<slug>.svg.
// Tech names come from `httpx -tech-detect` (wappalyzergo), which shares this vocabulary.
import { execFile } from 'node:child_process';
import { mkdtemp, mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const run = promisify(execFile);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'static', 'tech-icons');
const TARBALL = 'https://codeload.github.com/enthec/webappanalyzer/tar.gz/refs/heads/main';
const MAX_BYTES = 32 * 1024;

export const techIconSlug = (name) =>
	name
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-|-$/g, '');

const NAMED = { black: 0, white: 1, currentcolor: 0 };

const luma = (hex) => {
	const h = hex.length === 3 ? [...hex].map((c) => c + c).join('') : hex;
	const n = parseInt(h, 16);
	return (0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)) / 255;
};

const openTag = (svg) => {
	const i = svg.search(/<svg[\s>]/i);
	if (i < 0) return null;
	const j = svg.indexOf('>', i);
	return j < 0 ? null : { start: i, end: j + 1 };
};

function contrastPlate(svg) {
	const tag = openTag(svg);
	if (!tag) return null;
	const body = svg.slice(tag.end);
	const lumas = [];
	for (const m of body.matchAll(/(?:fill|stroke|stop-color)\s*[=:]\s*"?\s*([^;"'\s>)]+)/g)) {
		const v = m[1].toLowerCase();
		if (v === 'none') continue;
		if (v.startsWith('url')) return null;
		if (/^#[0-9a-f]{3}$|^#[0-9a-f]{6}$/.test(v)) lumas.push(luma(v.slice(1)));
		else if (v in NAMED) lumas.push(NAMED[v]);
		else return null;
	}
	if (!lumas.length) return '#fff';
	if (lumas.every((l) => l <= 0.22)) return '#fff';
	if (lumas.every((l) => l >= 0.86)) return '#18181b';
	return null;
}

function withPlate(svg, fill) {
	const tag = openTag(svg);
	if (!tag) return svg;
	const rect = `<rect width="100%" height="100%" rx="12%" fill="${fill}"/>`;
	return svg.slice(0, tag.end) + rect + svg.slice(tag.end);
}

async function main() {
	const tmp = await mkdtemp(join(tmpdir(), 'tech-icons-'));
	try {
		process.stdout.write('fetching webappanalyzer…\n');
		const res = await fetch(TARBALL);
		if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
		const tar = join(tmp, 'repo.tar.gz');
		await writeFile(tar, Buffer.from(await res.arrayBuffer()));
		await run('tar', ['-xzf', tar, '-C', tmp, '--strip-components=1']);

		const techDir = join(tmp, 'src', 'technologies');
		const iconDir = join(tmp, 'src', 'images', 'icons');
		const icons = new Map();
		for (const file of await readdir(techDir)) {
			if (!file.endsWith('.json')) continue;
			const doc = JSON.parse(await readFile(join(techDir, file), 'utf8'));
			for (const [name, def] of Object.entries(doc)) {
				if (def?.icon) icons.set(name, def.icon);
			}
		}

		await rm(OUT, { recursive: true, force: true });
		await mkdir(OUT, { recursive: true });

		let written = 0;
		let plated = 0;
		let aliased = 0;
		const claimed = new Set();
		const skipped = { missing: 0, raster: 0, oversized: 0, collided: 0 };
		for (const [name, icon] of icons) {
			if (!icon.endsWith('.svg')) {
				skipped.raster++;
				continue;
			}
			const src = join(iconDir, icon);
			if (!existsSync(src)) {
				skipped.missing++;
				continue;
			}
			const svg = await readFile(src, 'utf8');
			const min = svg
				.replace(/<!--[\s\S]*?-->/g, '')
				.replace(/<(metadata|title|desc)\b[\s\S]*?<\/\1>/g, '')
				.replace(/>\s+</g, '><')
				.trim();
			if (Buffer.byteLength(min) > MAX_BYTES) {
				skipped.oversized++;
				continue;
			}
			const slug = techIconSlug(name);
			if (claimed.has(slug)) {
				skipped.collided++;
				continue;
			}
			claimed.add(slug);
			const plate = contrastPlate(min);
			if (plate) plated++;
			const out = plate ? withPlate(min, plate) : min;
			await writeFile(join(OUT, `${slug}.svg`), out);
			written++;
			// several technologies share one logo file, so key it by brand too (Google Web Server -> google)
			const brand = techIconSlug(icon.replace(/\.svg$/, ''));
			if (brand && !claimed.has(brand)) {
				claimed.add(brand);
				await writeFile(join(OUT, `${brand}.svg`), out);
				aliased++;
			}
		}

		process.stdout.write(
			`wrote ${written} icons + ${aliased} brand aliases to static/tech-icons ` +
				`(${plated} plated for contrast) ` +
				`(skipped ${skipped.raster} raster, ${skipped.oversized} oversized, ` +
				`${skipped.collided} slug collisions, ${skipped.missing} missing)\n`
		);
	} finally {
		await rm(tmp, { recursive: true, force: true });
	}
}

main().catch((err) => {
	process.stderr.write(`tech icons unavailable: ${err.message}\n`);
	process.exit(0);
});
