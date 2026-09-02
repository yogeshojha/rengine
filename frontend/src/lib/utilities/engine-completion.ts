import type { Completion, CompletionContext, CompletionResult } from '@codemirror/autocomplete';
import type { EditorState, Line } from '@codemirror/state';
import type { EngineCatalog, StageCatalogEntry, StageField } from '$lib/types/scan-engine';
import { INTENSITIES, INTENSITY_HELP } from '$lib/types/scan-engine';

const TOP_LEVEL: { name: string; detail: string; info: string }[] = [
	{ name: 'name', detail: 'string', info: 'What this engine is called.' },
	{ name: 'description', detail: 'string', info: 'Optional note about what it is for.' },
	{
		name: 'intensity',
		detail: 'passive | normal | aggressive',
		info: 'Passive blocks every stage that sends traffic to the target.'
	},
	{
		name: 'global_threads',
		detail: 'integer',
		info: 'Baseline concurrency, scaled by a scan context.'
	},
	{ name: 'stages', detail: 'mapping', info: 'Per-stage settings, keyed by stage name.' }
];

function indentOf(text: string): number {
	return text.length - text.trimStart().length;
}

/** Keys enclosing the cursor's line, outermost first — e.g. ['stages', 'port_scan']. */
function pathAt(state: EditorState, line: Line): string[] {
	const path: string[] = [];
	let indent = indentOf(line.text);
	for (let n = line.number - 1; n >= 1; n--) {
		const prev = state.doc.line(n);
		const text = prev.text;
		if (!text.trim() || text.trimStart().startsWith('#')) continue;
		const i = indentOf(text);
		if (i >= indent) continue;
		const key = /^\s*(?:-\s*)?([\w-]+):/.exec(text);
		if (key) path.unshift(key[1]);
		indent = i;
		if (i === 0) break;
	}
	return path;
}

function fieldValues(field: StageField): Completion[] {
	if (field.type === 'boolean') {
		return [
			{ label: 'true', type: 'keyword' },
			{ label: 'false', type: 'keyword' }
		];
	}
	if (field.options) {
		return field.options.map((option) => ({ label: option, type: 'enum' }));
	}
	if (field.default !== null && field.default !== undefined && !Array.isArray(field.default)) {
		return [{ label: String(field.default), type: 'constant', detail: 'default' }];
	}
	return [];
}

function fieldDetail(field: StageField): string {
	const bits: string[] = [field.type];
	if (field.minimum !== null && field.maximum !== null)
		bits.push(`${field.minimum}–${field.maximum}`);
	if (field.default !== null && field.default !== undefined && field.default !== '') {
		bits.push(`default ${Array.isArray(field.default) ? field.default.join(', ') : field.default}`);
	}
	return bits.join(' · ');
}

function fieldInfo(field: StageField): string | undefined {
	const parts = [field.description ?? ''];
	if (field.scale) parts.push('A scan context can scale this.');
	const text = parts.filter(Boolean).join(' ');
	return text || undefined;
}

function stageCompletions(catalog: EngineCatalog, used: Set<string>): Completion[] {
	return catalog.stages
		.filter((s) => !used.has(s.name))
		.map((stage) => ({
			label: stage.name,
			type: 'class',
			detail: `${stage.phase} · L${stage.level}`,
			info: [stage.description, stage.tools.length ? `Tools: ${stage.tools.join(', ')}` : '']
				.filter(Boolean)
				.join('\n'),
			apply: `${stage.name}:\n    `
		}));
}

function usedStages(state: EditorState): Set<string> {
	const used = new Set<string>();
	let inStages = false;
	for (let n = 1; n <= state.doc.lines; n++) {
		const text = state.doc.line(n).text;
		if (/^stages:/.test(text)) {
			inStages = true;
			continue;
		}
		if (inStages && text.trim() && indentOf(text) === 0) inStages = false;
		if (!inStages) continue;
		const m = /^\s{2}([\w-]+):/.exec(text);
		if (m) used.add(m[1]);
	}
	return used;
}

export function engineCompletion(getCatalog: () => EngineCatalog | null) {
	return (context: CompletionContext): CompletionResult | null => {
		const catalog = getCatalog();
		if (!catalog) return null;

		const line = context.state.doc.lineAt(context.pos);
		const upto = line.text.slice(0, context.pos - line.from);
		if (upto.trimStart().startsWith('#')) return null;

		const path = pathAt(context.state, line);
		const stage: StageCatalogEntry | undefined =
			path[0] === 'stages' && path[1] ? catalog.stages.find((s) => s.name === path[1]) : undefined;

		// value position — after "key:" on this line
		const afterKey = /^\s*([\w-]+):\s+(\S*)$/.exec(upto);
		if (afterKey) {
			const [, key, typed] = afterKey;
			const from = context.pos - typed.length;
			if (path.length === 0 && key === 'intensity') {
				return {
					from,
					options: INTENSITIES.map((i) => ({ label: i, type: 'enum', info: INTENSITY_HELP[i] }))
				};
			}
			const field = stage?.fields.find((f) => f.name === key);
			if (field) {
				const options = fieldValues(field);
				return options.length ? { from, options } : null;
			}
			return null;
		}

		// list item under a field that has a fixed option set
		const listItem = /^\s*-\s*([\w.-]*)$/.exec(upto);
		if (listItem && stage) {
			const field = stage.fields.find((f) => f.name === path[2]);
			if (field?.options) {
				return {
					from: context.pos - listItem[1].length,
					options: field.options.map((o) => ({ label: o, type: 'enum' }))
				};
			}
			return null;
		}

		// key position
		const keyTyped = /^\s*([\w-]*)$/.exec(upto);
		if (!keyTyped) return null;
		const from = context.pos - keyTyped[1].length;

		if (path.length === 0) {
			return {
				from,
				options: TOP_LEVEL.map((t) => ({
					label: t.name,
					type: 'property',
					detail: t.detail,
					info: t.info,
					apply: t.name === 'stages' ? 'stages:\n  ' : `${t.name}: `
				}))
			};
		}
		if (path.length === 1 && path[0] === 'stages') {
			return { from, options: stageCompletions(catalog, usedStages(context.state)) };
		}
		if (stage) {
			const present = new Set(
				context.state.doc
					.toString()
					.split('\n')
					.filter((l) => indentOf(l) === 4)
					.map((l) => /^\s*([\w-]+):/.exec(l)?.[1] ?? '')
			);
			return {
				from,
				options: stage.fields
					.filter((f) => f.name === keyTyped[1] || !present.has(f.name))
					.map((field) => ({
						label: field.name,
						type: 'property',
						detail: fieldDetail(field),
						info: fieldInfo(field),
						apply: `${field.name}: `
					}))
			};
		}
		return null;
	};
}
