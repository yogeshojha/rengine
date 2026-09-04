<script lang="ts">
	import { SEVERITY_FILL, SEVERITY_LABELS } from '$lib/config/vulnerabilities';
	import type { SeverityCount } from '$lib/utilities/vulns';

	interface Props {
		counts: SeverityCount[];
		height?: string;
		onPick?: (severity: string) => void;
	}

	let { counts, height = 'h-2', onPick }: Props = $props();

	let total = $derived(counts.reduce((n, c) => n + c.count, 0));
	let parts = $derived(counts.filter((c) => c.count > 0));
</script>

{#if total > 0}
	<div class="flex w-full overflow-hidden rounded-full bg-muted {height}">
		{#each parts as part (part.severity)}
			{@const share = (part.count / total) * 100}
			{#if onPick}
				<button
					type="button"
					class="h-full transition-opacity hover:opacity-80"
					style="width:{share}%;background:{SEVERITY_FILL[part.severity]}"
					aria-label="{part.count} {SEVERITY_LABELS[part.severity]}"
					onclick={() => onPick(part.severity)}
				></button>
			{:else}
				<div
					class="h-full"
					style="width:{share}%;background:{SEVERITY_FILL[part.severity]}"
					aria-label="{part.count} {SEVERITY_LABELS[part.severity]}"
				></div>
			{/if}
		{/each}
	</div>
{/if}
