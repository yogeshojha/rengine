<script lang="ts">
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import TimelineRow from './timeline-row.svelte';
	import {
		FLAG_HELP,
		LEGEND_STATES,
		STATE_CELL,
		STATE_QUERY,
		WEB_STATE_LABELS,
		WebAssetState,
		type TimelineFlag
	} from '$lib/config/timeline';
	import type { TimelineSearchResult } from '$lib/types/timeline';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import { TIMELINE_COLUMNS, TIMELINE_LEAD_COLUMNS } from './timeline-columns';
	import StripHeader from './strip-header.svelte';

	interface Props {
		result: TimelineSearchResult;
		loading: boolean;
		apex?: string;
		selectedId: string | null;
		focusedIndex: number;
		pad: string;
		flag: TimelineFlag | null;
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
		onOpen: (s: SubdomainRead) => void;
		onOpenAt: (s: SubdomainRead, scanId: string) => void;
		/** opens the Timeline of an earlier run */
		onOpenScan: (scanId: string) => void;
		onQuery: (token: string) => void;
		onGone: () => void;
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
		onQuery,
		onGone,
		track
	}: Props = $props();

	let scans = $derived(result.scans);
	let highlight = $state(-1);
	let windowNote = $derived(
		result.runs > scans.length ? `Last ${scans.length} of ${result.runs} scans` : ''
	);

	function legendPick(state: WebAssetState) {
		if (state === WebAssetState.GONE) return onGone();
		const token = STATE_QUERY[state];
		if (token) onQuery(token);
	}
</script>

<ScrollArea orientation="horizontal">
	<StripHeader
		leadColumns={TIMELINE_LEAD_COLUMNS}
		columns={TIMELINE_COLUMNS}
		{scans}
		{sortKey}
		{sortDir}
		openLabel="Open this scan's Timeline"
		bind:highlight
		{onSort}
		{onOpenScan}
	/>

	<div
		class="divide-y divide-border/50 transition-opacity {loading ? 'opacity-60' : ''}"
		{@attach track}
	>
		{#each result.items as row, i (row.host.id)}
			<TimelineRow
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
	{#each LEGEND_STATES as state (state)}
		{@const filters = state === WebAssetState.GONE || !!STATE_QUERY[state]}
		<button
			type="button"
			class="flex items-center gap-1.5 rounded-md px-2 py-1 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/70 {filters
				? 'hover:bg-muted hover:text-foreground'
				: 'cursor-default'}"
			disabled={!filters}
			aria-label={filters ? `Show ${WEB_STATE_LABELS[state].toLowerCase()} web assets` : undefined}
			onclick={() => legendPick(state)}
		>
			<span
				class="h-3 w-2.5 shrink-0 rounded-[2px] {STATE_CELL[state] || 'border border-border'}"
				aria-hidden="true"
			></span>
			{WEB_STATE_LABELS[state]}
		</button>
	{/each}
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span class="relative h-3 w-2.5 shrink-0 rounded-[2px] bg-fill-success" aria-hidden="true">
			<span
				class="absolute top-1/2 left-1/2 size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-foreground ring-1 ring-card"
			></span>
		</span>
		Attribute changed
	</span>
	<span class="flex items-center gap-1.5 px-2 py-1">
		<span
			class="h-3 w-2.5 shrink-0 rounded-[2px] bg-fill-success outline outline-offset-1 outline-foreground/70"
			aria-hidden="true"
		></span>
		This scan
	</span>
	<span class="ml-auto flex flex-wrap items-center gap-x-3 px-2 py-1">
		{#if windowNote}<span>{windowNote}</span>{/if}
		{#if flag}<span>{FLAG_HELP[flag]}</span>{/if}
	</span>
</div>
