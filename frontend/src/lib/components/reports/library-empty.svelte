<script lang="ts">
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import { Button } from '$lib/components/ui/button';
	import EmptyState from '$lib/components/empty-state.svelte';

	let { title, onClear }: { title: string; onClear?: () => void } = $props();
</script>

<div class="p-6">
	<EmptyState icon={FileTextIcon} {title}>
		{#if onClear}
			<Button variant="outline" size="sm" onclick={onClear}>Clear filters</Button>
		{/if}
	</EmptyState>
</div>
