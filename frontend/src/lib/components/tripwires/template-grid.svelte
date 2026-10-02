<script lang="ts">
	import type { ChoiceSpec, TripwireTemplate } from '$lib/types/tripwire';
	import { dimensionSpec } from '$lib/config/tripwires';
	import Hint from '$lib/components/hint.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import QueryChip from './query-chip.svelte';

	interface Props {
		templates: TripwireTemplate[];
		groups: ChoiceSpec[];
		onPick: (template: TripwireTemplate) => void;
		columns?: string;
	}

	let { templates, groups, onPick, columns = 'sm:grid-cols-2 lg:grid-cols-3' }: Props = $props();
</script>

<div class="flex flex-col gap-5">
	{#each groups as group (group.key)}
		{@const rows = templates.filter((t) => t.group === group.key)}
		{#if rows.length > 0}
			<section class="flex flex-col gap-2">
				<SectionHead title={group.label} />
				<div class="grid gap-2 {columns}">
					{#each rows as template (template.key)}
						{@const spec = dimensionSpec(template.dimension)}
						<Hint text={template.query}>
							{#snippet child(props)}
								<button
									{...props}
									type="button"
									class="flex flex-col items-start gap-1.5 rounded-lg border p-3 text-left transition-colors hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
									onclick={() => onPick(template)}
								>
									<span class="text-sm font-medium">{template.name}</span>
									<span class="text-2xs text-muted-foreground">{spec.label}</span>
									<QueryChip
										dimension={template.dimension}
										query={template.query}
										hint={false}
										class="max-w-full"
									/>
								</button>
							{/snippet}
						</Hint>
					{/each}
				</div>
			</section>
		{/if}
	{/each}
</div>
