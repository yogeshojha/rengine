import { SvelteSet } from 'svelte/reactivity';
import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
import { SELECT_NONE } from '$lib/constants';
import {
	MAX_SCAN_BATCH,
	type ScanBatchCreate,
	type ScanRead,
	type StageOverrides
} from '$lib/types/scan';
import {
	DEFAULT_INTENSITY,
	type Intensity,
	type StageCatalogEntry,
	type StageConfig
} from '$lib/types/scan-engine';
import { summarize, type EngineSummary } from '$lib/utilities/engine-summary';
import {
	CAPABILITY,
	baselineStages,
	cloneStages,
	diffStages,
	mergeStages,
	resolvePlan,
	stageApplies,
	type LaunchMode,
	type PlanResolution,
	type StoredPlan
} from '$lib/utilities/launch-plan';

export interface TargetChip {
	key: string;
	id: string | null;
	value: string;
	type: string;
}

export class LaunchState {
	targets = $state<TargetChip[]>([]);
	mode = $state<LaunchMode>('quick');
	engineId = $state<string | null>(null);
	patch = $state<StageOverrides>({});
	intensity = $state<Intensity | null>(null);
	contextId = $state<string>(SELECT_NONE);
	private savedQuick: { stages: StageOverrides; intensity: Intensity | null } | null = null;

	readonly catalog = $derived(engineCatalogStore.catalog);
	readonly engine = $derived(
		this.engineId ? (scanEnginesStore.engines.find((e) => e.id === this.engineId) ?? null) : null
	);
	readonly defaults = $derived(
		this.catalog ? baselineStages(this.catalog.stages, null) : ({} as Record<string, StageConfig>)
	);
	readonly baseline = $derived(
		this.catalog
			? baselineStages(this.catalog.stages, this.engine)
			: ({} as Record<string, StageConfig>)
	);
	readonly effective = $derived(mergeStages(this.baseline, this.patch));
	readonly baseIntensity = $derived<Intensity>(this.engine?.intensity ?? DEFAULT_INTENSITY);
	readonly runIntensity = $derived<Intensity>(this.intensity ?? this.baseIntensity);
	readonly targetTypes = $derived([...new SvelteSet(this.targets.map((t) => t.type))]);
	readonly lensType = $derived(this.targets[0]?.type ?? null);
	readonly resolution = $derived<PlanResolution | null>(
		this.catalog
			? resolvePlan(this.catalog, this.effective, this.lensType, this.runIntensity)
			: null
	);
	readonly overrides = $derived<StageOverrides>(
		diffStages(this.baseline, this.resolution?.effective ?? this.effective)
	);
	readonly applicableStages = $derived<StageCatalogEntry[]>(
		this.catalog ? this.catalog.stages.filter((s) => stageApplies(s, this.targetTypes)) : []
	);
	readonly quickStages = $derived<StageCatalogEntry[]>(
		this.applicableStages.filter((s) => s.role === CAPABILITY)
	);
	readonly runningStages = $derived<StageCatalogEntry[]>(
		this.catalog && this.resolution
			? this.catalog.stages.filter((s) => {
					const state = this.resolution!.states.get(s.name);
					return (state === 'on' || state === 'implied') && stageApplies(s, this.targetTypes);
				})
			: []
	);
	readonly summary = $derived<EngineSummary | null>(
		this.catalog && this.resolution
			? summarize(this.resolution.effective, this.applicableStages, this.runIntensity)
			: null
	);
	readonly blockReason = $derived.by<string | null>(() => {
		if (this.mode === 'engine' && !this.engine) return 'Select a scan engine.';
		if (this.targets.length === 0) return 'Add at least one target.';
		if (this.targets.length > MAX_SCAN_BATCH) return `Select at most ${MAX_SCAN_BATCH} targets.`;
		if (this.catalog && this.runningStages.length === 0) return 'Select at least one stage.';
		return null;
	});
	readonly canLaunch = $derived(this.blockReason === null && !!this.catalog);

	stageState(name: string) {
		return this.resolution?.states.get(name) ?? 'off';
	}

	toggleStage(name: string) {
		const next = !this.effective[name]?.enabled;
		this.setStageField(name, 'enabled', next);
	}

	setStageField(name: string, field: string, value: unknown) {
		const current = { ...(this.patch[name] ?? {}) };
		if (JSON.stringify(value) === JSON.stringify(this.baseline[name]?.[field]))
			delete current[field];
		else current[field] = value;
		const next = { ...this.patch };
		if (Object.keys(current).length) next[name] = current;
		else delete next[name];
		this.patch = next;
	}

	setStageFields(name: string, fields: StageConfig) {
		for (const [field, value] of Object.entries(fields)) this.setStageField(name, field, value);
	}

	resetStage(name: string) {
		const next = { ...this.patch };
		delete next[name];
		this.patch = next;
	}

	// a remembered selection is applied over a cleared board so stage defaults never leak back in
	private capabilityPatch(patch: StageOverrides): StageOverrides {
		const next: StageOverrides = {};
		for (const stage of this.catalog?.stages ?? []) {
			if (stage.role !== CAPABILITY) continue;
			const stored = patch[stage.name];
			if (stored) next[stage.name] = { enabled: false, ...stored };
			else if (this.baseline[stage.name]?.enabled) next[stage.name] = { enabled: false };
		}
		return next;
	}

	selectAll() {
		const next: StageOverrides = {};
		for (const stage of this.quickStages) {
			if (!this.baseline[stage.name]?.enabled) next[stage.name] = { enabled: true };
		}
		this.patch = next;
	}

	clearAll() {
		const next: StageOverrides = {};
		for (const stage of this.catalog?.stages ?? []) {
			if (stage.role === CAPABILITY && this.baseline[stage.name]?.enabled) {
				next[stage.name] = { enabled: false };
			}
		}
		this.patch = next;
	}

	rememberQuick(stages: StageOverrides, intensity: Intensity | null) {
		this.savedQuick = { stages: cloneStages(stages), intensity };
	}

	useQuick() {
		this.mode = 'quick';
		this.engineId = null;
		if (this.savedQuick) {
			this.patch = this.capabilityPatch(cloneStages(this.savedQuick.stages));
			this.intensity = this.savedQuick.intensity;
		} else {
			this.intensity = null;
			this.clearAll();
		}
	}

	applyEngine(id: string | null) {
		if (this.mode === 'quick' && Object.keys(this.patch).length) {
			this.savedQuick = { stages: cloneStages(this.patch), intensity: this.intensity };
		}
		this.mode = 'engine';
		this.engineId = id;
		this.patch = {};
		this.intensity = null;
	}

	applyStored(plan: StoredPlan, engineExists: (id: string) => boolean) {
		if (plan.mode === 'engine') {
			if (!plan.engineId || !engineExists(plan.engineId)) return false;
			this.applyEngine(plan.engineId);
			return true;
		}
		this.mode = 'quick';
		this.engineId = null;
		this.patch = this.capabilityPatch(cloneStages(plan.stages));
		this.intensity = plan.intensity;
		return true;
	}

	restoreRun(scan: ScanRead, engineExists: (id: string) => boolean) {
		const config = scan.execution_config;
		this.contextId = scan.context_id ?? SELECT_NONE;
		if (scan.engine_id && engineExists(scan.engine_id)) {
			this.applyEngine(scan.engine_id);
			return;
		}
		this.mode = 'quick';
		this.engineId = null;
		this.patch = this.capabilityPatch(cloneStages(config.overrides ?? {}));
		this.intensity =
			config.intensity && config.intensity !== DEFAULT_INTENSITY
				? (config.intensity as Intensity)
				: null;
	}

	addTarget(chip: TargetChip) {
		if (this.targets.some((t) => t.key === chip.key)) return;
		this.targets = [...this.targets, chip];
	}

	removeTarget(key: string) {
		this.targets = this.targets.filter((t) => t.key !== key);
	}

	stored(): StoredPlan {
		return {
			mode: this.mode,
			engineId: this.mode === 'engine' ? this.engineId : null,
			stages: this.mode === 'quick' ? cloneStages(this.patch) : {},
			intensity: this.mode === 'quick' ? this.intensity : null,
			contextId: this.contextId === SELECT_NONE ? null : this.contextId
		};
	}

	body(): ScanBatchCreate {
		const engine = this.mode === 'engine';
		return {
			engine_id: engine ? this.engineId : null,
			context_id: this.contextId === SELECT_NONE ? null : this.contextId,
			target_ids: this.targets.filter((t) => t.id).map((t) => t.id as string),
			target_values: this.targets.filter((t) => !t.id).map((t) => t.value),
			overrides: engine ? {} : this.overrides,
			intensity: engine ? null : this.intensity
		};
	}

	reset() {
		this.savedQuick = null;
		this.targets = [];
		this.mode = 'quick';
		this.engineId = null;
		this.patch = {};
		this.intensity = null;
		this.contextId = SELECT_NONE;
	}
}
