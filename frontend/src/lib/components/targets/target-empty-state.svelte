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
	}

	let { hasFilters, onAddTarget, onClearFilters }: Props = $props();
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
		<Empty.Title>{hasFilters ? 'No matching targets' : 'No targets'}</Empty.Title>
		{#if !hasFilters}
			<Empty.Description>
				<p>Add a domain, IP address, IP range, URL or ASN.</p>
			</Empty.Description>
		{/if}
	</Empty.Header>
	<Empty.Content>
		<div class="flex gap-2">
			{#if hasFilters}
				<Button variant="outline" onclick={onClearFilters}>Clear filters</Button>
			{:else}
				<Button onclick={onAddTarget}>Add target</Button>
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
		Documentation <ArrowUpRightIcon class="inline" />
	</Button>
</Empty.Root>
