<script lang="ts">
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import SectionField from '$lib/components/reports/builder/section-field.svelte';
	import type { SectionCatalogEntry } from '$lib/types/report';
	import type { ReportPlan } from './report-plan.svelte';

	interface Props {
		section: SectionCatalogEntry;
		plan: ReportPlan;
		hideLaunchFields?: boolean;
	}

	let { section, plan, hideLaunchFields = false }: Props = $props();

	let fields = $derived(section.fields.filter((f) => !(hideLaunchFields && f.launch)));
	let changed = $derived(plan.changedFields(section.name));
	let values = $derived(plan.config(section.name));
</script>

<Popover.Root>
	<Popover.Trigger>
		{#snippet child({ props })}
			<button
				{...props}
				type="button"
				class="inline-flex items-center gap-1 rounded-r-md px-2 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50"
				aria-label="Settings for {section.title}"
			>
				<SlidersHorizontal class="size-3" />
				{#if changed.length}<span class="size-1.5 rounded-full bg-primary"></span>{/if}
			</button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content class="w-[26rem] max-w-[calc(100vw-2rem)] p-3" align="start">
		<div class="mb-2 flex items-start justify-between gap-3">
			<div class="min-w-0">
				<p class="text-sm font-medium">{section.title}</p>
				<p class="text-[11px] text-muted-foreground">Applies to this report only.</p>
			</div>
			{#if changed.length}
				<Button
					variant="ghost"
					size="sm"
					class="h-6 shrink-0 gap-1 px-1.5 text-xs text-muted-foreground"
					onclick={() => plan.resetSection(section.name)}
				>
					<RotateCcw class="size-3" /> Reset
				</Button>
			{/if}
		</div>
		{#if fields.length}
			<div class="divide-y divide-border">
				{#each fields as field (field.name)}
					<SectionField
						{field}
						value={values[field.name] ?? field.default}
						onChange={(value) => plan.setField(section.name, field.name, value)}
					/>
				{/each}
			</div>
		{:else}
			<p class="text-xs text-muted-foreground">This section has nothing to configure.</p>
		{/if}
	</Popover.Content>
</Popover.Root>
