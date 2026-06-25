<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';

	interface Props {
		tech: string[];
		max?: number;
		class?: string;
	}

	let { tech, max = 4, class: className = '' }: Props = $props();

	let shown = $derived(tech.slice(0, max));
	let extra = $derived(Math.max(0, tech.length - max));
</script>

{#if tech.length}
	<div class="flex flex-wrap gap-1 {className}">
		{#each shown as t (t)}
			<Badge variant="outline" class="font-normal">{t}</Badge>
		{/each}
		{#if extra}
			<Badge variant="outline" class="font-normal text-muted-foreground">+{extra}</Badge>
		{/if}
	</div>
{:else}
	<span class="text-xs text-muted-foreground">—</span>
{/if}
