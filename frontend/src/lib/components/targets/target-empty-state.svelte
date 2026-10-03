<script lang="ts">
	import CrosshairIcon from '@lucide/svelte/icons/crosshair';
	import Funnel from '@lucide/svelte/icons/funnel';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import ArrowUpRightIcon from '@lucide/svelte/icons/arrow-up-right';

	interface Props {
		hasFilters: boolean;
		onAddTarget: () => void;
		onClearFilters?: () => void;
	}

	let { hasFilters, onAddTarget, onClearFilters }: Props = $props();
</script>

<EmptyState
	compact
	icon={hasFilters ? Funnel : CrosshairIcon}
	title={hasFilters ? 'No matching targets' : 'No targets'}
	description={hasFilters ? undefined : 'Add a domain, IP address, IP range, URL or ASN.'}
	class="border-0 bg-transparent py-16"
>
	{#if hasFilters}
		<Button size="sm" variant="outline" onclick={onClearFilters}>Clear filters</Button>
	{:else}
		<Button size="sm" onclick={onAddTarget}>Add target</Button>
	{/if}
	<Button
		href="https://rengine.wiki"
		target="_blank"
		rel="noreferrer"
		variant="link"
		class="text-muted-foreground"
		size="sm"
	>
		Documentation <ArrowUpRightIcon />
	</Button>
</EmptyState>
