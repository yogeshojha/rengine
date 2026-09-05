import type { EnginePreset } from '$lib/types/scan-engine';
import type { StageOverrides } from '$lib/types/scan';
import { cloneStages, readLastPlan, rememberLastPlan } from '$lib/utilities/launch-plan';

export type QuickScanSelection =
	| { kind: 'recipe'; preset: string }
	| { kind: 'engine'; engineId: string };

export interface QuickScanPrefs {
	enabled: boolean;
	selection: QuickScanSelection | null;
	contextId: string | null;
}

export const encodeSelection = (s: QuickScanSelection) =>
	s.kind === 'recipe' ? `recipe:${s.preset}` : `engine:${s.engineId}`;

export function decodeSelection(value: string): QuickScanSelection | null {
	const [kind, ...rest] = value.split(':');
	const id = rest.join(':');
	if (!id) return null;
	if (kind === 'recipe') return { kind: 'recipe', preset: id };
	if (kind === 'engine') return { kind: 'engine', engineId: id };
	return null;
}

export function defaultSelection(presets: EnginePreset[]): QuickScanSelection | null {
	return presets.length ? { kind: 'recipe', preset: presets[0].name } : null;
}

export function quickScanPlan(
	selection: QuickScanSelection,
	presets: EnginePreset[]
): { engine_id: string | null; overrides: StageOverrides } {
	if (selection.kind === 'engine') return { engine_id: selection.engineId, overrides: {} };
	const preset = presets.find((p) => p.name === selection.preset);
	return { engine_id: null, overrides: cloneStages(preset?.stages ?? {}) };
}

function selectionFromStored(
	stored: { engineId: string | null; stages: StageOverrides },
	presets: EnginePreset[]
): QuickScanSelection | null {
	if (stored.engineId) return { kind: 'engine', engineId: stored.engineId };
	const signature = JSON.stringify(stored.stages);
	const preset = presets.find((p) => JSON.stringify(p.stages) === signature);
	return preset ? { kind: 'recipe', preset: preset.name } : null;
}

export function readQuickScanPrefs(storageKey: string, presets: EnginePreset[]): QuickScanPrefs {
	if (typeof localStorage === 'undefined')
		return { enabled: false, selection: null, contextId: null };
	const stored = readLastPlan();
	return {
		enabled: localStorage.getItem(storageKey) === '1',
		selection: stored ? selectionFromStored(stored, presets) : null,
		contextId: stored?.contextId ?? null
	};
}

export function rememberQuickScanToggle(storageKey: string, enabled: boolean) {
	if (typeof localStorage === 'undefined') return;
	localStorage.setItem(storageKey, enabled ? '1' : '0');
}

export function rememberQuickScanChoice(
	selection: QuickScanSelection,
	contextId: string | null,
	presets: EnginePreset[]
) {
	const plan = quickScanPlan(selection, presets);
	rememberLastPlan({
		mode: plan.engine_id ? 'engine' : 'quick',
		engineId: plan.engine_id,
		stages: plan.overrides,
		intensity: null,
		contextId
	});
}
