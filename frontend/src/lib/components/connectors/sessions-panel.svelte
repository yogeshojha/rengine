<script lang="ts">
	import { untrack } from 'svelte';
	import HistoryIcon from '@lucide/svelte/icons/history';
	import * as Card from '$lib/components/ui/card/index.js';
	import EmptyState from '$lib/components/empty-state.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { connectors } from '$lib/stores/connectors.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import type { Connector } from '$lib/types/connector';

	let { connector, projectId }: { connector: Connector; projectId: string } = $props();

	const rows = $derived(connectors.sessions);

	$effect(() => {
		const id = connector.id;
		untrack(() => void connectors.loadSessions(id, projectId));
	});
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead title="Sessions" description="Recorded traffic grouped by period of activity">
		<span class="tabular-nums">{rows.length}</span>
	</PanelHead>

	{#if rows.length === 0}
		<div class="px-4 py-10">
			<EmptyState icon={HistoryIcon} title="No sessions" />
		</div>
	{:else}
		<div class="divide-y">
			{#each rows as row (row.id)}
				<div class="space-y-1 px-5 py-4">
					<div class="flex flex-wrap items-baseline justify-between gap-2">
						<span class="text-sm">{relativeTime(row.started_at)}</span>
						<span class="text-muted-foreground text-xs tabular-nums">
							{row.requests.toLocaleString()} requests · {row.novel} new shapes
						</span>
					</div>
					<p class="text-muted-foreground truncate font-mono text-xs">{row.hosts.join(', ')}</p>
					{#if row.client}
						<p class="text-muted-foreground/70 text-2xs">{row.client}</p>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</Card.Root>
