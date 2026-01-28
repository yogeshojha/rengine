<script lang="ts">
	import { CrosshairIcon, Funnel } from 'lucide-svelte';
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
		<Empty.Title></Empty.Title>
		<Empty.Description>
			{#if hasFilters}
				No targets match the current filters.
			{:else}
				<p>
					Get started by adding your first target. Targets are the domains, IPs, and other assets
					you want to monitor.
				</p>
				<p>Currently supported targets are domain, IP Addresses, IP Range, ASN and URL.</p>
			{/if}
		</Empty.Description>
	</Empty.Header>
	<Empty.Content>
		<div class="flex gap-2">
			{#if hasFilters}
				<Button variant="outline" onclick={onClearFilters}>Clear Filters</Button>
			{:else}
				<Button onclick={onAddTarget}>Add new Target</Button>
				<!-- TODO: Import functionality -->
				<Button variant="outline">Import Target</Button>
			{/if}
		</div>
	</Empty.Content>
	<Button variant="link" class="text-muted-foreground" size="sm">
		<!-- TODO: Update link -->
		<a href="https://rengine.wiki">
			Learn More <ArrowUpRightIcon class="inline" />
		</a>
	</Button>
</Empty.Root>
