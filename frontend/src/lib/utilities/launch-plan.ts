import type {
	EngineCatalog,
	Intensity,
	ScanEngine,
	StageCatalogEntry,
	StageConfig
} from '$lib/types/scan-engine';
import type { StageOverrides } from '$lib/types/scan';
import { STORAGE_KEYS } from '$lib/config/storage-keys';

export type StageState = 'on' | 'off' | 'implied' | 'blocked';

export type LaunchMode = 'quick' | 'engine';

export interface LaunchPlan {
	mode: LaunchMode;
	engineId: string | null;
	stages: StageOverrides;
	intensity: Intensity | null;
}

export interface PlanResolution {
	states: Map<string, StageState>;
	implied: Set<string>;
	unsatisfied: Set<string>;
	effective: Record<string, StageConfig>;
}

// state proxies cannot be structuredClone'd; plans are plain JSON
export const cloneStages = (stages: StageOverrides): StageOverrides =>
	JSON.parse(JSON.stringify(stages ?? {}));

export function baselineStages(
	stages: StageCatalogEntry[],
	engine: ScanEngine | null
): Record<string, StageConfig> {
	const out: Record<string, StageConfig> = {};
	for (const stage of stages) {
		out[stage.name] = { ...stage.defaults, ...(engine?.stages?.[stage.name] ?? {}) };
	}
	return out;
}

export function mergeStages(
	base: Record<string, StageConfig>,
	patch: StageOverrides
): Record<string, StageConfig> {
	const out: Record<string, StageConfig> = {};
	for (const [name, config] of Object.entries(base)) {
		out[name] = { ...config, ...(patch[name] ?? {}) };
	}
	return out;
}

export function diffStages(
	base: Record<string, StageConfig>,
	effective: Record<string, StageConfig>
): StageOverrides {
	const out: StageOverrides = {};
	for (const [name, config] of Object.entries(effective)) {
		const changed: StageConfig = {};
		for (const [field, value] of Object.entries(config)) {
			if (JSON.stringify(value) !== JSON.stringify(base[name]?.[field])) changed[field] = value;
		}
		if (Object.keys(changed).length) out[name] = changed;
	}
	return out;
}

export function stageApplies(stage: StageCatalogEntry, targetTypes: string[]): boolean {
	return targetTypes.length === 0 || targetTypes.some((t) => stage.applies_to.includes(t));
}

function levelsOf(catalog: EngineCatalog, targetType: string | null): StageCatalogEntry[][] {
	const phaseIndex = new Map(catalog.phases.map((p, i) => [p, i]));
	const groups = new Map<string, StageCatalogEntry[]>();
	for (const stage of catalog.stages) {
		if (targetType && !stage.applies_to.includes(targetType)) continue;
		const key = `${phaseIndex.get(stage.phase) ?? 99}:${stage.level}`;
		groups.set(key, [...(groups.get(key) ?? []), stage]);
	}
	return [...groups.entries()]
		.sort(([a], [b]) => {
			const [pa, la] = a.split(':').map(Number);
			const [pb, lb] = b.split(':').map(Number);
			return pa - pb || la - lb;
		})
		.map(([, stages]) => stages);
}

function producerRank(stage: StageCatalogEntry): [number, number, number, number] {
	return [
		stage.touches_target ? 1 : 0,
		stage.consumes.length,
		stage.defaults.enabled ? 0 : 1,
		stage.level
	];
}

function pickProducer(
	consumer: StageCatalogEntry,
	earlier: StageCatalogEntry[],
	chosen: Set<string>,
	blocked: (stage: StageCatalogEntry) => boolean
): StageCatalogEntry | null {
	const candidates = earlier.filter(
		(s) =>
			!chosen.has(s.name) &&
			!blocked(s) &&
			s.produces.some((kind) => consumer.consumes.includes(kind))
	);
	candidates.sort((a, b) => {
		const ra = producerRank(a);
		const rb = producerRank(b);
		for (let i = 0; i < ra.length; i++) if (ra[i] !== rb[i]) return ra[i] - rb[i];
		return a.name.localeCompare(b.name);
	});
	return candidates[0] ?? null;
}

export function mostRecentEngine(engines: ScanEngine[]): ScanEngine | null {
	if (!engines.length) return null;
	return [...engines].sort((a, b) => (b.last_used_at ?? '').localeCompare(a.last_used_at ?? ''))[0];
}

export const CAPABILITY = 'capability';
export const SUPPORT = 'support';

// quick: selected capabilities pull in producers and fed support stages follow; engine: runs as stored
export function resolvePlan(
	catalog: EngineCatalog,
	effective: Record<string, StageConfig>,
	targetType: string | null,
	intensity: Intensity,
	quick = true
): PlanResolution {
	const passive = intensity === 'passive';
	const blocked = (stage: StageCatalogEntry) => passive && stage.touches_target;
	const levels = levelsOf(catalog, targetType);
	const applicable = levels.flat();
	const selected = new Set(
		applicable
			.filter((s) => (!quick || s.role === CAPABILITY) && Boolean(effective[s.name]?.enabled))
			.map((s) => s.name)
	);
	const chosen = new Set(selected);
	const implied = new Set<string>();
	const unsatisfied = new Set<string>();

	let changed = true;
	while (changed) {
		changed = false;
		unsatisfied.clear();
		const active = applicable.some((s) => chosen.has(s.name) && s.touches_target && !blocked(s));
		const available = new Set(targetType ? (catalog.seed_produces[targetType] ?? []) : []);
		const earlier: StageCatalogEntry[] = [];
		for (const level of levels) {
			const produced = new Set<string>();
			for (const stage of level) {
				const fed = stage.consumes.length === 0 || stage.consumes.some((k) => available.has(k));
				if (chosen.has(stage.name)) {
					if (blocked(stage)) continue;
					if (!fed) {
						const producer = quick ? pickProducer(stage, earlier, chosen, blocked) : null;
						if (producer) {
							chosen.add(producer.name);
							implied.add(producer.name);
							changed = true;
							break;
						}
						unsatisfied.add(stage.name);
						continue;
					}
					for (const kind of stage.produces) produced.add(kind);
					continue;
				}
				if (
					quick &&
					selected.size > 0 &&
					stage.role === SUPPORT &&
					fed &&
					!blocked(stage) &&
					(!stage.touches_target || active)
				) {
					chosen.add(stage.name);
					implied.add(stage.name);
					changed = true;
					break;
				}
			}
			if (changed) break;
			for (const kind of produced) available.add(kind);
			earlier.push(...level);
		}
	}

	const states = new Map<string, StageState>();
	for (const stage of catalog.stages) {
		if (!chosen.has(stage.name)) states.set(stage.name, 'off');
		else if (blocked(stage)) states.set(stage.name, 'blocked');
		else if (implied.has(stage.name)) states.set(stage.name, 'implied');
		else states.set(stage.name, 'on');
	}
	const merged: Record<string, StageConfig> = { ...effective };
	if (quick) {
		for (const stage of applicable) {
			merged[stage.name] = { ...merged[stage.name], enabled: chosen.has(stage.name) };
		}
	}
	return { states, implied, unsatisfied, effective: merged };
}

export interface StoredPlan extends LaunchPlan {
	contextId: string | null;
}

export function readLastPlan(): StoredPlan | null {
	try {
		const raw = localStorage.getItem(STORAGE_KEYS.launchLastPlan);
		if (!raw) return null;
		const parsed = JSON.parse(raw) as Partial<StoredPlan>;
		if (typeof parsed !== 'object' || parsed === null) return null;
		const engineId = typeof parsed.engineId === 'string' ? parsed.engineId : null;
		return {
			mode: parsed.mode === 'engine' || (parsed.mode !== 'quick' && engineId) ? 'engine' : 'quick',
			engineId,
			stages: parsed.stages && typeof parsed.stages === 'object' ? parsed.stages : {},
			intensity: (parsed.intensity as Intensity | null) ?? null,
			contextId: typeof parsed.contextId === 'string' ? parsed.contextId : null
		};
	} catch {
		return null;
	}
}

export function rememberLastPlan(plan: StoredPlan) {
	try {
		localStorage.setItem(STORAGE_KEYS.launchLastPlan, JSON.stringify(plan));
	} catch {}
}
