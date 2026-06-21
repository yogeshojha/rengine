<script lang="ts">
	import type { Target } from '$lib/types/target';
	import type { TargetDetailRead } from '$lib/types/target-detail';
	import { buildTargetSummary } from './derive';
	import Vital from './vital.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';

	interface Props {
		target: Target;
		detail: TargetDetailRead | null;
		loading?: boolean;
	}

	let { target, detail, loading = false }: Props = $props();

	const summary = $derived(buildTargetSummary(target, detail));
</script>

<section class="space-y-2">
	<div class="flex items-center gap-2">
		<h2 class="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground/70">
			At a glance
		</h2>
		<span class="flex-1 h-px bg-border/40"></span>
	</div>

	{#if loading && summary.vitals.length === 0}
		<div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-2">
			{#each Array(4) as _, i (i)}
				<div class="rounded-lg border bg-card px-3 py-2.5 space-y-2">
					<Skeleton class="h-2.5 w-16" />
					<Skeleton class="h-4 w-24" />
				</div>
			{/each}
		</div>
	{:else if summary.vitals.length > 0}
		<div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-2">
			{#each summary.vitals as vital (vital.key)}
				<Vital {vital} />
			{/each}
		</div>
	{:else}
		<div class="rounded-lg border border-dashed bg-card/40 px-4 py-6 text-center">
			<p class="text-xs text-muted-foreground/60">
				No enrichment data yet — run enrichment to populate this summary.
			</p>
		</div>
	{/if}
</section>
