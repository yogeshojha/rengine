<script lang="ts">
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import { Button } from '$lib/components/ui/button';
	import EmptyState from '$lib/components/empty-state.svelte';

	let { title, onClear }: { title: string; onClear?: () => void } = $props();
</script>

<EmptyState icon={FileTextIcon} {title} class="rounded-none border-0 bg-transparent py-16">
	{#if onClear}
		<Button variant="outline" size="sm" onclick={onClear}>Clear filters</Button>
	{/if}
</EmptyState>
