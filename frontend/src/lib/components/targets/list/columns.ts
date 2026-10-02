import type { TargetColumn } from './prefs.svelte';

export const TCOL = {
	select: 'hidden w-5 shrink-0 items-center @xl/targets:flex',
	target: 'min-w-0 flex-1',
	run: 'flex w-[132px] shrink-0',
	findings: 'flex w-[150px] shrink-0',
	assets: 'flex w-[208px] shrink-0',
	change: 'flex w-[96px] shrink-0',
	organizations: 'flex w-[150px] shrink-0',
	tags: 'flex w-[150px] shrink-0',
	actions: 'flex w-[92px] shrink-0 justify-end'
} as const;

export const TNARROW = {
	spark: 'hidden @3xl/targets:block'
} as const;

export const TCOL_PX: Record<TargetColumn, number> = {
	run: 132,
	findings: 150,
	assets: 208,
	change: 96,
	organizations: 150,
	tags: 150
};

// the order columns take the room left beside the target column
export const FIT_ORDER: readonly TargetColumn[] = [
	'findings',
	'run',
	'assets',
	'change',
	'organizations',
	'tags'
];

// columns whose values move into the target cell when they get no room
export const FOLDED_INTO_TARGET: ReadonlySet<TargetColumn> = new Set(['run', 'findings']);

const GAP_PX = 12;
const ROW_PAD_PX = 32;
const ACTIONS_PX = 92;
const SELECT_PX = 20;
const SELECT_FROM_PX = 576;
const TARGET_MIN_PX = 240;

export function fitColumns(width: number, chosen: readonly TargetColumn[]): Set<TargetColumn> {
	const fitted = new Set<TargetColumn>();
	let room = width - ROW_PAD_PX - ACTIONS_PX - GAP_PX - TARGET_MIN_PX;
	if (width >= SELECT_FROM_PX) room -= SELECT_PX + GAP_PX;
	for (const column of FIT_ORDER) {
		if (!chosen.includes(column)) continue;
		const need = TCOL_PX[column] + GAP_PX;
		if (need > room) break;
		room -= need;
		fitted.add(column);
	}
	return fitted;
}
