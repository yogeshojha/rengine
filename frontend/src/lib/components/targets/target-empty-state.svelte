<script lang="ts">
	import CrosshairIcon from '@lucide/svelte/icons/crosshair';
	import Funnel from '@lucide/svelte/icons/funnel';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import ArrowUpRightIcon from '@lucide/svelte/icons/arrow-up-right';

	interface Props {
		hasFilters: boolean;
		onAddTarget: () => void;
		onClearFilters?: () => void;
		onImport?: () => void;
		filterSummary?: string;
	}

	let { hasFilters, onAddTarget, onClearFilters, onImport, filterSummary }: Props = $props();
</script>

<Empty.Root>
	<Empty.Header>
		<Empty.Media variant="icon">
			{#if hasFilters}
				<Funnel />
			{:else}
				<CrosshairIcon />
			{/if}
		</Empty.Media>
		<Empty.Title>{hasFilters ? 'No matching targets' : 'No targets yet'}</Empty.Title>
		<Empty.Description>
			{#if hasFilters}
				No targets match the current filters.
				{#if filterSummary}
					<p class="mt-1 text-xs">Filtered by: {filterSummary}</p>
				{/if}
			{:else}
				<p>
					Add a target to begin. A target is a domain, IP address, IP range, URL or ASN this project
					monitors.
				</p>
			{/if}
		</Empty.Description>
	</Empty.Header>
	<Empty.Content>
		<div class="flex gap-2">
			{#if hasFilters}
				<Button variant="outline" onclick={onClearFilters}>Clear filters</Button>
			{:else}
				<Button onclick={onAddTarget}>Add target</Button>
				{#if onImport}
					<Button variant="outline" onclick={onImport}>Import targets</Button>
				{/if}
			{/if}
		</div>
	</Empty.Content>
	<Button
		href="https://rengine.wiki"
		target="_blank"
		rel="noreferrer"
		variant="link"
		class="text-muted-foreground"
		size="sm"
	>
		Learn more <ArrowUpRightIcon class="inline" />
	</Button>
</Empty.Root>
