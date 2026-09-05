<script lang="ts">
	import type { Target } from '$lib/types/target';
	import type { TargetDetailRead } from '$lib/types/target-detail';
	import { buildTargetSummary } from './derive';
	import Vital from './vital.svelte';
	import * as Card from '$lib/components/ui/card';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';

	interface Props {
		target: Target;
		detail: TargetDetailRead | null;
		loading?: boolean;
	}

	let { target, detail, loading = false }: Props = $props();

	const summary = $derived(buildTargetSummary(target, detail));
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead title="Identity" description="Registration and routing facts for this target" />
	{#if loading && summary.vitals.length === 0}
		<div class="-mt-px -ml-px grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
			{#each Array(4) as _, i (i)}
				<div class="flex flex-col gap-2 border-t border-l px-5 py-4">
					<Skeleton class="h-3 w-20" />
					<Skeleton class="h-4 w-28" />
					<Skeleton class="h-3 w-16" />
				</div>
			{/each}
		</div>
	{:else if summary.vitals.length > 0}
		<div class="-mt-px -ml-px grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
			{#each summary.vitals as vital (vital.key)}
				<Vital {vital} />
			{/each}
		</div>
	{:else}
		<p class="px-5 py-8 text-center text-sm text-muted-foreground">
			No enrichment data yet. Refresh enrichment to populate this panel.
		</p>
	{/if}
</Card.Root>
