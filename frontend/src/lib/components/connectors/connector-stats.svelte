<script lang="ts">
	import PauseIcon from '@lucide/svelte/icons/pause';
	import PlayIcon from '@lucide/svelte/icons/play';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { CONNECTOR_STATE_DOT, CONNECTOR_STATE_LABELS } from '$lib/config/connectors';
	import { relativeTime } from '$lib/utilities/dates';
	import type { Connector } from '$lib/types/connector';

	let { connector, onTogglePause }: { connector: Connector; onTogglePause: () => void } = $props();

	const cells = $derived([
		{
			key: 'shapes',
			label: 'Request shapes',
			value: connector.candidates,
			note: 'captured by this connector'
		},
		{
			key: 'queued',
			label: 'Queued',
			value: connector.queued,
			note: connector.sync_trigger === 'manual' ? 'manual trigger' : 'awaiting trigger'
		},
		{
			key: 'unseen',
			label: 'Not found by scans',
			value: connector.unseen,
			note: 'recorded only by this connector'
		},
		{
			key: 'requests',
			label: 'Requests received',
			value: connector.requests_seen,
			note: 'before deduplication'
		},
		{
			key: 'unassigned',
			label: 'Unassigned',
			value: connector.unassigned,
			note: connector.only_known_hosts
				? `${connector.dropped_out_of_scope} discarded`
				: 'no target matched yet'
		},
		{
			key: 'scans',
			label: 'Scans launched',
			value: connector.scans_launched,
			note: connector.last_scan_at ? relativeTime(connector.last_scan_at) : 'none yet'
		}
	]);
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead title={connector.name}>
		<span class="flex items-center gap-1.5">
			<span class="size-1.5 rounded-full {CONNECTOR_STATE_DOT[connector.state]}"></span>
			{CONNECTOR_STATE_LABELS[connector.state]}
		</span>
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

	<div class="-ml-px grid grid-cols-2 sm:grid-cols-3">
		{#each cells as cell (cell.key)}
			<div class="flex min-w-0 flex-col gap-1 border-t border-l px-5 py-4">
				<span class="text-muted-foreground text-[11px] tracking-wide uppercase">{cell.label}</span>
				<span class="text-2xl leading-7 font-semibold tabular-nums"
					>{cell.value.toLocaleString()}</span
				>
				<span class="text-muted-foreground truncate text-xs">{cell.note}</span>
			</div>
		{/each}
	</div>
</Card.Root>
