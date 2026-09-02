import { isMap, isPair, isSeq, parseDocument, stringify, type Document } from 'yaml';
import type {
	EngineCatalog,
	ScanEngine,
	StageCatalogEntry,
	StageConfig
} from '$lib/types/scan-engine';

export interface YamlIssue {
	line: number;
	from: number;
	to: number;
	severity: 'error' | 'warning';
	message: string;
}

export interface EngineDraft {
	name: string;
	description: string | null;
	intensity: string;
	global_threads: number;
	stages: Record<string, StageConfig>;
}

const TOP_LEVEL = ['name', 'description', 'intensity', 'global_threads', 'stages'] as const;

export function overridesOf(config: StageConfig, defaults: StageConfig): StageConfig {
	return Object.fromEntries(
		Object.entries(config ?? {}).filter(
			([key, value]) => JSON.stringify(value) !== JSON.stringify(defaults[key])
		)
	);
}

function materializeStages(
	stages: Record<string, StageConfig>,
	catalog: EngineCatalog | null
): Record<string, StageConfig> {
	if (!catalog) return {};
	const out: Record<string, StageConfig> = {};
	for (const spec of catalog.stages) {
		out[spec.name] = { ...spec.defaults, ...(stages?.[spec.name] ?? {}) };
	}
	return out;
}

export function engineToYaml(engine: ScanEngine, catalog: EngineCatalog | null): string {
	const shape: Record<string, unknown> = { name: engine.name };
	if (engine.description) shape.description = engine.description;
	shape.intensity = engine.intensity;
	shape.global_threads = engine.global_threads;
	shape.stages = materializeStages(engine.stages ?? {}, catalog);
	return stringify(shape, { indent: 2, lineWidth: 0, nullStr: '~' });
}

export function parse(source: string): Document.Parsed {
	return parseDocument(source, { keepSourceTokens: true });
}

export function setStageField(
	doc: Document.Parsed,
	stage: string,
	field: string,
	value: unknown
): void {
	doc.setIn(['stages', stage, field], value);
}

export function deleteStage(doc: Document.Parsed, stage: string): void {
	doc.deleteIn(['stages', stage]);
}

export function pruneEmptyStages(doc: Document.Parsed): void {
	const stages = doc.get('stages') as { items?: { key: { value: string } }[] } | undefined;
	if (!stages?.items) return;
	for (const item of [...stages.items]) {
		const name = item.key.value;
		const value = doc.getIn(['stages', name], true) as { items?: unknown[] } | undefined;
		if (value?.items && value.items.length === 0) doc.deleteIn(['stages', name]);
	}
}

export function draftFromDoc(doc: Document.Parsed): EngineDraft | null {
	const raw = toPlain(doc);
	if (!raw) return null;
	return {
		name: String(raw.name ?? ''),
		description: (raw.description as string) ?? null,
		intensity: String(raw.intensity ?? 'normal'),
		global_threads: Number(raw.global_threads ?? 30),
		stages: (raw.stages as Record<string, StageConfig>) ?? {}
	};
}

// toJS() throws on alias bombs and cyclic refs — never let that reach a $derived
function toPlain(doc: Document.Parsed): Record<string, unknown> | null {
	try {
		const raw = doc.toJS() as Record<string, unknown> | null;
		return raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : null;
	} catch {
		return null;
	}
}

function rangeOf(doc: Document.Parsed, path: (string | number)[]): [number, number] | null {
	const node = doc.getIn(path, true) as { range?: [number, number, number] } | undefined;
	return node?.range ? [node.range[0], node.range[1]] : null;
}

function lineAt(source: string, offset: number): number {
	return source.slice(0, offset).split('\n').length;
}

function near(value: string, options: string[]): string | null {
	const lower = value.toLowerCase();
	const hit = options.find(
		(o) => o.toLowerCase().includes(lower) || lower.includes(o.toLowerCase())
	);
	return hit ?? null;
}

export function validate(
	source: string,
	doc: Document.Parsed,
	catalog: EngineCatalog | null
): YamlIssue[] {
	const issues: YamlIssue[] = [];
	const push = (path: (string | number)[], severity: YamlIssue['severity'], message: string) => {
		const range = rangeOf(doc, path) ?? [0, Math.min(source.length, 1)];
		issues.push({
			line: lineAt(source, range[0]),
			from: range[0],
			to: Math.max(range[1], range[0] + 1),
			severity,
			message
		});
	};

	for (const error of doc.errors) {
		issues.push({
			line: lineAt(source, error.pos[0]),
			from: error.pos[0],
			to: Math.max(error.pos[1], error.pos[0] + 1),
			severity: 'error',
			message: error.message
		});
	}
	if (doc.errors.length || !catalog) return issues;

	const raw = toPlain(doc);
	if (!raw) {
		return [
			{
				line: 1,
				from: 0,
				to: 1,
				severity: 'error',
				message: 'Engine must be a plain YAML mapping (aliases and cycles are not supported).'
			}
		];
	}

	if (!String(raw.name ?? '').trim()) push(['name'], 'error', 'An engine needs a name.');

	const intensities = ['passive', 'normal', 'aggressive'];
	if (raw.intensity !== undefined && !intensities.includes(String(raw.intensity))) {
		push(['intensity'], 'error', `intensity must be one of ${intensities.join(', ')}.`);
	}

	for (const key of Object.keys(raw)) {
		if (!(TOP_LEVEL as readonly string[]).includes(key)) {
			const hint = near(key, [...TOP_LEVEL]);
			push([key], 'warning', `Unknown key '${key}'.${hint ? ` Did you mean '${hint}'?` : ''}`);
		}
	}

	const stages = raw.stages;
	if (stages === undefined) return issues;
	if (typeof stages !== 'object' || stages === null || Array.isArray(stages)) {
		push(['stages'], 'error', 'stages must be a mapping of stage name to settings.');
		return issues;
	}

	const known = new Map(catalog.stages.map((s) => [s.name, s]));
	for (const [stageName, config] of Object.entries(stages as Record<string, unknown>)) {
		const spec = known.get(stageName);
		if (!spec) {
			const hint = near(stageName, [...known.keys()]);
			push(
				['stages', stageName],
				'error',
				`Unknown stage '${stageName}'.${hint ? ` Did you mean '${hint}'?` : ''}`
			);
			continue;
		}
		if (typeof config !== 'object' || config === null || Array.isArray(config)) {
			push(['stages', stageName], 'error', `'${stageName}' settings must be a mapping.`);
			continue;
		}
		for (const [key, value] of Object.entries(config as Record<string, unknown>)) {
			const field = spec.fields.find((f) => f.name === key);
			if (!field) {
				const hint = near(
					key,
					spec.fields.map((f) => f.name)
				);
				push(
					['stages', stageName, key],
					'error',
					`'${stageName}' has no setting '${key}'.${hint ? ` Did you mean '${hint}'?` : ''}`
				);
				continue;
			}
			for (const issue of checkField(spec, field.name, value)) {
				push(['stages', stageName, key], 'error', issue);
			}
		}
	}
	return issues;
}

function checkField(spec: StageCatalogEntry, name: string, value: unknown): string[] {
	const field = spec.fields.find((f) => f.name === name);
	if (!field) return [];
	const out: string[] = [];
	const label = `${spec.name}.${name}`;

	if (field.type === 'boolean' && typeof value !== 'boolean') {
		out.push(`${label} must be true or false.`);
	} else if (field.type === 'array') {
		if (!Array.isArray(value)) out.push(`${label} must be a list.`);
		else if (field.options) {
			const bad = value.filter((v) => !field.options!.includes(String(v)));
			if (bad.length) {
				out.push(`${label}: unknown value${bad.length > 1 ? 's' : ''} ${bad.join(', ')}.`);
			}
		}
	} else if (field.type === 'integer' || field.type === 'number') {
		if (typeof value !== 'number') out.push(`${label} must be a number.`);
		else {
			if (field.minimum !== null && value < field.minimum) {
				out.push(`${label} must be at least ${field.minimum}.`);
			}
			if (field.maximum !== null && value > field.maximum) {
				out.push(`${label} must be at most ${field.maximum}.`);
			}
		}
	} else if (field.options && !field.options.includes(String(value))) {
		out.push(`${label} must be one of ${field.options.join(', ')}.`);
	}
	return out;
}

export function stageRange(doc: Document.Parsed, stage: string): [number, number] | null {
	return rangeOf(doc, ['stages', stage]);
}

export interface StageBlock {
	name: string;
	from: number;
	to: number;
}

type Ranged = { range?: [number, number, number] } | null | undefined;

export function stageBlocks(doc: Document.Parsed): StageBlock[] {
	const stages = doc.get('stages', true);
	if (!isMap(stages)) return [];
	const out: StageBlock[] = [];
	for (const item of stages.items) {
		const key = item.key as Ranged & { value?: unknown };
		const name = String(key?.value ?? '');
		if (!name || !key?.range) continue;
		const value = item.value as Ranged;
		out.push({ name, from: key.range[0], to: value?.range?.[1] ?? key.range[1] });
	}
	return out;
}

export function stageAtOffset(doc: Document.Parsed, offset: number): string | null {
	return stageBlocks(doc).find((b) => offset >= b.from && offset <= b.to)?.name ?? null;
}

function spans(item: unknown, offset: number): boolean {
	let from: number | undefined;
	let to: number | undefined;
	if (isPair(item)) {
		from = (item.key as Ranged)?.range?.[0];
		to = (item.value as Ranged)?.range?.[2] ?? (item.key as Ranged)?.range?.[2];
	} else {
		const range = (item as Ranged)?.range;
		from = range?.[0];
		to = range?.[2];
	}
	return from !== undefined && to !== undefined && offset >= from && offset <= to;
}

export function pathAtOffset(doc: Document.Parsed, offset: number): string[] {
	const path: string[] = [];
	let node: unknown = doc.contents;
	while (node) {
		if (isMap(node)) {
			const hit = node.items.find((p) => spans(p, offset));
			if (!hit) break;
			path.push(String((hit.key as { value?: unknown }).value ?? ''));
			node = hit.value;
		} else if (isSeq(node)) {
			const index = node.items.findIndex((n) => spans(n, offset));
			if (index < 0) break;
			path.push(String(index));
			node = node.items[index];
		} else break;
	}
	return path;
}

export function formatYaml(source: string): string {
	const doc = parse(source);
	return doc.errors.length ? source : String(doc);
}
