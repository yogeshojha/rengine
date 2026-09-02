import type { EngineCatalog, StageCatalogEntry, StageConfig } from '$lib/types/scan-engine';

export type Footprint = 'none' | 'quiet' | 'moderate' | 'loud';

export const FOOTPRINT_LABEL: Record<Footprint, string> = {
	none: 'No target traffic',
	quiet: 'Quiet',
	moderate: 'Moderate',
	loud: 'Loud'
};

export const FOOTPRINT_HELP: Record<Footprint, string> = {
	none: 'All enabled stages use public data sources. No traffic is sent to the target.',
	quiet: 'Sends a low volume of traffic to the target.',
	moderate: 'Sends a moderate volume of traffic to the target.',
	loud: 'Sends a high volume of traffic to the target. Likely to trigger rate limiting or WAF blocking.'
};

const MODERATE_RPS = 300;
const LOUD_RPS = 1000;

export function footprintFor(requestsPerSecond: number, touchesTarget: boolean): Footprint {
	if (!touchesTarget) return 'none';
	if (requestsPerSecond >= LOUD_RPS) return 'loud';
	if (requestsPerSecond >= MODERATE_RPS) return 'moderate';
	return 'quiet';
}

export interface EngineSummary {
	activeStages: number;
	totalStages: number;
	tools: string[];
	footprint: Footprint;
	requestsPerSecond: number;
	touchesTarget: boolean;
	headline: string;
}

function enabled(stage: StageCatalogEntry, stages: Record<string, StageConfig>): boolean {
	return Boolean(stages?.[stage.name]?.enabled ?? stage.defaults.enabled);
}

function rateOf(stage: StageCatalogEntry, config: StageConfig): number {
	let total = 0;
	for (const field of stage.fields) {
		if (field.scale !== 'rate') continue;
		const value = config?.[field.name] ?? stage.defaults[field.name];
		if (typeof value === 'number') total += value;
	}
	return total;
}

export function summarize(
	stages: Record<string, StageConfig>,
	catalog: EngineCatalog | StageCatalogEntry[] | null,
	intensity: string
): EngineSummary {
	const all = Array.isArray(catalog) ? catalog : (catalog?.stages ?? []);
	const active = all.filter((s) => enabled(s, stages));
	const passiveMode = intensity === 'passive';
	const running = passiveMode ? active.filter((s) => !s.touches_target) : active;

	const loud = running.filter((s) => s.touches_target);
	const requestsPerSecond = loud.reduce((n, s) => n + rateOf(s, stages?.[s.name] ?? {}), 0);

	const footprint = footprintFor(requestsPerSecond, loud.length > 0);

	const tools = [...new Set(running.flatMap((s) => s.tools))].sort();

	const parts = [`${running.length} of ${all.length} stages`];
	if (footprint === 'none') parts.push('no target traffic');
	else parts.push(`~${requestsPerSecond}/s to target`);
	if (passiveMode && active.length !== running.length) {
		parts.push(`${active.length - running.length} blocked by passive`);
	}

	return {
		activeStages: running.length,
		totalStages: all.length,
		tools,
		footprint,
		requestsPerSecond,
		touchesTarget: loud.length > 0,
		headline: parts.join(' · ')
	};
}
