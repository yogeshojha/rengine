<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import { dashboardLayout } from '$lib/stores/dashboard-layout.svelte';

	let hidden = $derived(dashboardLayout.hiddenWidgets);
</script>

{#if hidden.length}
	<div
		class="flex flex-wrap items-center gap-2 border-t border-dashed pt-3 text-xs text-muted-foreground"
	>
		<span>Hidden</span>
		{#each hidden as w (w.id)}
			<button
				type="button"
				class="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs hover:text-foreground"
				onclick={() => dashboardLayout.show(w.id)}
			>
				<Plus class="size-3" />
				{w.label}
			</button>
		{/each}
	</div>
{/if}
