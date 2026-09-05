<script lang="ts">
	import type { StageCatalogEntry } from '$lib/types/scan-engine';

	interface Props {
		stages: StageCatalogEntry[];
		implied?: Set<string>;
	}

	let { stages, implied = new Set<string>() }: Props = $props();
</script>

{#if stages.length === 0}
	<p class="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
		No stage runs with this plan.
	</p>
{:else}
	<div class="flex flex-wrap items-center gap-y-2 rounded-md border bg-card px-3 py-2.5">
		{#each stages as stage, i (stage.name)}
			{@const hollow = implied.has(stage.name)}
			{#if i > 0}
				<span
					class="mx-2.5 w-5 border-t-[1.5px] border-dotted border-muted-foreground/70"
					aria-hidden="true"
				></span>
			{/if}
			<span
				class="inline-flex items-center gap-2 text-[13px] {hollow
					? 'text-muted-foreground'
					: 'text-foreground'}"
			>
				<span
					class="size-2 shrink-0 rounded-full {hollow
						? 'border-[1.5px] border-muted-foreground bg-card'
						: 'bg-foreground'}"
				></span>
				{stage.title}
			</span>
		{/each}
	</div>
{/if}
