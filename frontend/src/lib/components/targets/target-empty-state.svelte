<script lang="ts">
	import { CrosshairIcon, Search, Plus } from 'lucide-svelte';
	import { Button } from '$lib/components/ui/button';

	interface Props {
		hasFilters: boolean;
		onAddTarget: () => void;
		onClearFilters?: () => void;
	}

	let { hasFilters, onAddTarget, onClearFilters }: Props = $props();
</script>

<div class="flex flex-col items-center justify-center py-16 px-4">
	<div
		class="h-16 w-16 rounded-full bg-muted/50 flex items-center justify-center mb-6"
	>
		{#if hasFilters}
			<Search class="h-8 w-8 text-muted-foreground/50" />
		{:else}
			<CrosshairIcon class="h-8 w-8 text-muted-foreground/50" />
		{/if}
	</div>

	{#if hasFilters}
		<h3 class="text-lg font-semibold mb-2">No targets match your filters</h3>
		<p class="text-sm text-muted-foreground text-center max-w-sm mb-6">
			Try adjusting your search query or clearing some filters to see more results.
		</p>
		<div class="flex items-center gap-3">
			{#if onClearFilters}
				<Button variant="outline" onclick={onClearFilters}>
					Clear filters
				</Button>
			{/if}
			<Button onclick={onAddTarget}>
				<Plus class="h-4 w-4 mr-2" />
				Add target
			</Button>
		</div>
	{:else}
		<h3 class="text-lg font-semibold mb-2">No targets yet</h3>
		<p class="text-sm text-muted-foreground text-center max-w-sm mb-6">
			Get started by adding your first target. Targets are the domains, IPs, and other assets you want to monitor. Currently supported targets are domain, IP Addresses, IP Range, ASN and URL.
		</p>
		<Button onclick={onAddTarget}>
			<Plus class="h-4 w-4 mr-2" />
			Add your first target
		</Button>
	{/if}
</div>
