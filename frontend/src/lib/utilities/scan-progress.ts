import type { ScanRead } from '$lib/types/scan';
import type { StageCatalogEntry } from '$lib/types/scan-engine';
import type { LiveRun } from '$lib/stores/live-scans.svelte';
import { formatSeconds } from '$lib/utilities/scan-status';

export function plannedStages(scan: ScanRead, catalog: StageCatalogEntry[]): StageCatalogEntry[] {
	const cfg = scan.execution_config.stages ?? {};
	const type = scan.execution_config.target_type;
	return catalog.filter(
		(s) => s.applies_to.includes(type) && (cfg[s.name]?.enabled ?? true) !== false
	);
}

export type StageStepState = 'done' | 'failed' | 'running' | 'pending';

export const STAGE_STEP_CLASS: Record<StageStepState, string> = {
	done: 'bg-info',
	failed: 'bg-destructive',
	running: 'bg-info/45 animate-pulse',
	pending: 'bg-muted-foreground/20'
};

export interface StageStep {
	name: string;
	title: string;
	state: StageStepState;
}

export interface StageProgress {
	done: number;
	total: number;
	percent: number;
	label: string;
	steps: StageStep[];
}

export function stageSteps(run: LiveRun | undefined, planned: StageCatalogEntry[]): StageStep[] {
	return planned.map((s) => ({
		name: s.name,
		title: s.title,
		state: run?.failed.includes(s.name)
			? 'failed'
			: run?.done.includes(s.name)
				? 'done'
				: run?.stage?.name === s.name
					? 'running'
					: 'pending'
	}));
}

export function etaLabel(
	previousSeconds: number | null,
	elapsedSeconds: number | null
): string | null {
	if (previousSeconds == null || elapsedSeconds == null) return null;
	const remaining = previousSeconds - elapsedSeconds;
	if (remaining > 0) return `~${formatSeconds(remaining)} left`;
	return `past last run (${formatSeconds(previousSeconds)})`;
}

export function stageProgress(
	scan: ScanRead,
	run: LiveRun | undefined,
	planned: StageCatalogEntry[]
): StageProgress {
	const total = planned.length;
	const done = planned.filter((s) => run?.done.includes(s.name)).length;
	const percent = total ? Math.round((done / total) * 100) : 0;
	let label: string;
	if (scan.status === 'pending') label = 'Queued';
	else if (run?.stage) label = run.stage.title;
	else if (total > 0 && done >= total) label = 'Publishing results';
	else label = 'Starting';
	return { done, total, percent, label, steps: stageSteps(run, planned) };
}
