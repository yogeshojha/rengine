<script lang="ts">
	import CrosshairIcon from '@lucide/svelte/icons/crosshair';
	import Funnel from '@lucide/svelte/icons/funnel';
	import Upload from '@lucide/svelte/icons/upload';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import ArrowUpRightIcon from '@lucide/svelte/icons/arrow-up-right';

	interface Props {
		hasFilters: boolean;
		/** Only when no other "Add target" button is on screen. */
		onAddTarget?: () => void;
		onImport?: () => void;
		onClearFilters?: () => void;
	}

	let { hasFilters, onAddTarget, onImport, onClearFilters }: Props = $props();
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
	{:else if onAddTarget || onImport}
		<div class="flex flex-wrap justify-center gap-2">
			{#if onAddTarget}
				<Button size="sm" onclick={onAddTarget}>Add target</Button>
			{/if}
			{#if onImport}
				<Button size="sm" variant="outline" onclick={onImport}>
					<Upload class="size-4" /> Import
				</Button>
			{/if}
		</div>
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
