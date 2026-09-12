<script lang="ts">
	import PauseIcon from '@lucide/svelte/icons/pause';
	import PlayIcon from '@lucide/svelte/icons/play';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { CONNECTOR_STATE_DOT, CONNECTOR_STATE_LABELS } from '$lib/config/connectors';
	import { relativeTime } from '$lib/utilities/dates';
	import type { CandidateQuery, Connector } from '$lib/types/connector';

	let {
		connector,
		onTogglePause,
		onPick
	}: {
		connector: Connector;
		onTogglePause: () => void;
		onPick: (query: CandidateQuery) => void;
	} = $props();

	const cells = $derived([
		{
			key: 'flagged',
			label: 'Flagged',
			value: connector.flagged,
			note: 'sensitive, administrative, server errors',
			tone: connector.flagged ? 'text-warning' : '',
			query: null
		},
		{
			key: 'unseen',
			label: 'Not found by scans',
			value: connector.unseen,
			note: 'not recorded by any scan',
			tone: connector.unseen ? 'text-info' : '',
			query: { known: false } as CandidateQuery
		},
		{
			key: 'out_of_scope',
			label: 'Out of scope',
			value: connector.out_of_scope,
			note: 'forbidden by a program',
			tone: connector.out_of_scope ? 'text-destructive' : '',
			query: { notice: 'out_of_scope' } as CandidateQuery
		},
		{
			key: 'pending',
			label: 'Waiting for Burp',
			value: connector.pending_actions,
			note: 'pending collection',
			tone: '',
			query: null
		}
	]);
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead title={connector.name}>
		<span class="flex items-center gap-1.5">
			<span class="size-1.5 rounded-full {CONNECTOR_STATE_DOT[connector.state]}"></span>
			{CONNECTOR_STATE_LABELS[connector.state]}
		</span>
		{#if connector.last_seen_at}
			<span>{relativeTime(connector.last_seen_at)}</span>
		{/if}
		{#if connector.last_client}
			<span>{connector.last_client}</span>
		{/if}
		<Button variant="outline" size="sm" class="h-7" onclick={onTogglePause}>
			{#if connector.paused}
				<PlayIcon class="size-3.5" />
				Resume
			{:else}
				<PauseIcon class="size-3.5" />
				Pause
			{/if}
		</Button>
	</PanelHead>

	<div class="-ml-px grid grid-cols-2 sm:grid-cols-4">
		{#each cells as cell (cell.key)}
			{#if cell.query && cell.value > 0}
				<button
					type="button"
					class="hover:bg-muted/40 flex min-w-0 cursor-pointer flex-col gap-1 border-t border-l px-5 py-4 text-left transition-colors"
					onclick={() => onPick(cell.query!)}
				>
					<span class="text-muted-foreground text-2xs tracking-wide uppercase">{cell.label}</span>
					<span class="text-2xl leading-7 font-semibold tabular-nums {cell.tone}"
						>{cell.value.toLocaleString()}</span
					>
					<span class="text-muted-foreground truncate text-xs">{cell.note}</span>
				</button>
			{:else}
				<div class="flex min-w-0 flex-col gap-1 border-t border-l px-5 py-4">
					<span class="text-muted-foreground text-2xs tracking-wide uppercase">{cell.label}</span>
					<span class="text-2xl leading-7 font-semibold tabular-nums {cell.tone}"
						>{cell.value.toLocaleString()}</span
					>
					<span class="text-muted-foreground truncate text-xs">{cell.note}</span>
				</div>
			{/if}
		{/each}
	</div>

	<div class="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 border-t px-5 py-2.5 text-xs">
		<span>{connector.requests_seen.toLocaleString()} requests received</span>
		<span>{connector.candidates.toLocaleString()} request shapes</span>
		{#if connector.unassigned}
			<span>{connector.unassigned.toLocaleString()} without a target</span>
		{/if}
		{#if connector.dropped_out_of_scope}
			<span>{connector.dropped_out_of_scope.toLocaleString()} discarded</span>
		{/if}
		{#if connector.scans_launched}
			<span
				>{connector.scans_launched.toLocaleString()} scans launched{connector.last_scan_at
					? ` · ${relativeTime(connector.last_scan_at)}`
					: ''}</span
			>
		{/if}
	</div>
</Card.Root>
