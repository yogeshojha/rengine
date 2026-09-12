<script lang="ts">
	import { untrack } from 'svelte';
	import CompassIcon from '@lucide/svelte/icons/compass';
	import * as Card from '$lib/components/ui/card/index.js';
	import EmptyState from '$lib/components/empty-state.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { connectors } from '$lib/stores/connectors.svelte';
	import type { Connector } from '$lib/types/connector';

	let { connector, projectId }: { connector: Connector; projectId: string } = $props();

	const rows = $derived(connectors.coverage);

	$effect(() => {
		const id = connector.id;
		untrack(() => void connectors.loadCoverage(id, projectId));
	});

	function share(row: { known_endpoints: number; visited: number }): number {
		return row.known_endpoints ? Math.round((row.visited / row.known_endpoints) * 100) : 0;
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead
		title="Coverage"
		description="Scan coverage against requests recorded by this connector"
	>
		<span class="tabular-nums">{rows.length} host{rows.length === 1 ? '' : 's'}</span>
	</PanelHead>

	{#if rows.length === 0}
		<div class="px-4 py-10">
			<EmptyState icon={CompassIcon} title="No coverage" />
		</div>
	{:else}
		<div class="divide-y">
			{#each rows as row (row.host)}
				<div class="space-y-2 px-5 py-4">
					<div class="flex flex-wrap items-baseline justify-between gap-2">
						<span class="font-mono text-sm">{row.host}</span>
						<span class="text-muted-foreground text-xs tabular-nums">
							{#if row.known_endpoints}
								{row.visited} of {row.known_endpoints} reached
							{:else}
								Not scanned
							{/if}
						</span>
					</div>

					{#if row.known_endpoints}
						<div class="bg-muted h-1 overflow-hidden rounded-full">
							<div class="bg-series h-full rounded-full" style="width: {share(row)}%"></div>
						</div>
					{/if}

					<div class="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 text-xs">
						{#if row.unvisited > 0}
							<span class="text-warning">{row.unvisited} not reached</span>
						{/if}
						{#if row.browsed_unknown > 0}
							<span class="text-info">{row.browsed_unknown} not found by any scan</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</Card.Root>
