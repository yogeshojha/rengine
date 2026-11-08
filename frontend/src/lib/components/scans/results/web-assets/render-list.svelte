<script lang="ts">
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import RenderRow from './render-row.svelte';
	import {
		RENDER_CELL,
		RENDER_FLAG_HELP,
		RENDER_LEGEND,
		RENDER_STATE_LABELS,
		RenderFlag,
		RenderState
	} from '$lib/config/timeline';
	import type { RenderSearchResult } from '$lib/types/timeline';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import { RENDER_COLUMNS, RENDER_LEAD_COLUMNS } from './timeline-columns';
	import StripHeader from './strip-header.svelte';

	interface Props {
		result: RenderSearchResult;
		loading: boolean;
		apex?: string;
		selectedId: string | null;
		focusedIndex: number;
		pad: string;
		flag: RenderFlag | null;
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
		onOpen: (s: SubdomainRead) => void;
		onOpenAt: (s: SubdomainRead, scanId: string) => void;
		/** opens the Screenshots view of an earlier run */
		onOpenScan: (scanId: string) => void;
		onFlag: (flag: RenderFlag) => void;
		track: (node: HTMLElement) => void | (() => void);
	}

	let {
		result,
		loading,
		apex = '',
		selectedId,
		focusedIndex,
		pad,
		flag,
		sortKey,
		sortDir,
		onSort,
		onOpen,
		onOpenAt,
		onOpenScan,
		onFlag,
		track
	}: Props = $props();

	let scans = $derived(result.scans);
	let highlight = $state(-1);
	let windowNote = $derived(
		result.runs > scans.length ? `Last ${scans.length} of ${result.runs} scans` : ''
	);

	const LEGEND_FLAG: Partial<Record<RenderState, RenderFlag>> = {
		[RenderState.CHANGED]: RenderFlag.CHANGED,
		[RenderState.NOT_CAPTURED]: RenderFlag.NOT_CAPTURED
	};
</script>

<ScrollArea orientation="horizontal">
	<StripHeader
		leadColumns={RENDER_LEAD_COLUMNS}
		columns={RENDER_COLUMNS}
		{scans}
		{sortKey}
		{sortDir}
		openLabel="Open this scan's screenshots"
		bind:highlight
		{onSort}
		{onOpenScan}
	/>

	<div
		class="divide-y divide-border/50 transition-opacity {loading ? 'opacity-60' : ''}"
		{@attach track}
	>
		{#each result.items as row, i (row.host.id)}
			<RenderRow
				{row}
				{scans}
				index={i}
				{apex}
				selected={selectedId === row.host.id}
				focused={focusedIndex === i}
				{pad}
				{highlight}
				onHover={(col) => (highlight = col)}
				{onOpen}
				{onOpenAt}
			/>
		{/each}
	</div>
</ScrollArea>

<div
	class="flex flex-wrap items-center gap-x-1 gap-y-1 border-t px-2 py-1.5 text-xs text-muted-foreground"
>
	{#each RENDER_LEGEND as state (state)}
		{@const target = LEGEND_FLAG[state]}
		<button
			type="button"
			class="flex items-center gap-1.5 rounded-md px-2 py-1 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/70 {target
				? 'hover:bg-muted hover:text-foreground'
				: 'cursor-default'}"
			disabled={!target}
			aria-label={target
				? `Show ${RENDER_STATE_LABELS[state].toLowerCase()} web assets`
				: undefined}
			onclick={() => target && onFlag(target)}
		>
			<span class="h-3 w-2.5 shrink-0 rounded-[2px] {RENDER_CELL[state]}" aria-hidden="true"></span>
			{RENDER_STATE_LABELS[state]}
		</button>
	{/each}
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span class="relative h-3 w-2.5 shrink-0 rounded-[2px] bg-fill-muted" aria-hidden="true">
			<span
				class="absolute inset-x-0 bottom-0 h-1 bg-[repeating-linear-gradient(135deg,var(--fill-hatch)_0_2px,transparent_2px_4px)]"
			></span>
		</span>
		Image removed
	</span>
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span
			class="h-3 w-2.5 shrink-0 rounded-[2px] bg-fill-muted outline outline-offset-1 outline-foreground/70"
			aria-hidden="true"
		></span>
		This scan
	</span>
	<span class="ml-auto flex flex-wrap items-center gap-x-3 px-2 py-1">
		{#if windowNote}<span>{windowNote}</span>{/if}
		{#if flag}<span>{RENDER_FLAG_HELP[flag]}</span>{/if}
	</span>
</div>
