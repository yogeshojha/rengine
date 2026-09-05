<script lang="ts">
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
	import * as Popover from '$lib/components/ui/popover';
	import { Button } from '$lib/components/ui/button';
	import StageFieldRow from '$lib/components/engines/stage-field.svelte';
	import VulnPlan from '$lib/components/scans/vuln-plan.svelte';
	import { VULN_STAGE } from '$lib/config/vulnerabilities';
	import type { StageCatalogEntry } from '$lib/types/scan-engine';
	import type { LaunchState } from './launch-state.svelte';

	interface Props {
		stage: StageCatalogEntry;
		launch: LaunchState;
	}

	let { stage, launch }: Props = $props();

	const VULN_PLAN_FIELDS = ['severities', 'template_sets'];

	let isVuln = $derived(stage.name === VULN_STAGE);
	let fields = $derived(
		stage.fields.filter(
			(f) => f.name !== 'enabled' && !(isVuln && VULN_PLAN_FIELDS.includes(f.name))
		)
	);
	let changedFields = $derived(
		Object.keys(launch.patch[stage.name] ?? {}).filter((f) => f !== 'enabled')
	);
	function applyVulnPlan(overrides: Record<string, Record<string, unknown>>) {
		const next = overrides[stage.name] ?? {};
		for (const field of VULN_PLAN_FIELDS) {
			launch.setStageField(stage.name, field, next[field] ?? launch.baseline[stage.name]?.[field]);
		}
	}

	function reset() {
		for (const field of changedFields) {
			launch.setStageField(stage.name, field, launch.baseline[stage.name]?.[field]);
		}
	}
</script>

<Popover.Root>
	<Popover.Trigger>
		{#snippet child({ props })}
			<button
				{...props}
				type="button"
				class="inline-flex items-center gap-1 rounded-r-md px-2 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50"
				aria-label="Settings for {stage.title}"
			>
				<SlidersHorizontal class="size-3" />
				{#if changedFields.length}
					<span class="size-1.5 rounded-full bg-primary"></span>
				{/if}
			</button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content class="w-[28rem] max-w-[calc(100vw-2rem)] p-3" align="start">
		<div class="mb-2 flex items-start justify-between gap-3">
			<div class="min-w-0">
				<p class="text-sm font-medium">{stage.title}</p>
				<p class="text-[11px] text-muted-foreground">Applies to this scan only.</p>
			</div>
			{#if changedFields.length}
				<Button
					variant="ghost"
					size="sm"
					class="h-6 shrink-0 gap-1 px-1.5 text-xs text-muted-foreground"
					onclick={reset}
				>
					<RotateCcw class="size-3" /> Reset
				</Button>
			{/if}
		</div>
		{#if isVuln}
			<VulnPlan
				engineStages={launch.engine?.stages ?? null}
				showEnabled={false}
				onChange={applyVulnPlan}
			/>
		{/if}
		{#if fields.length}
			<div class="divide-y divide-border {isVuln ? 'mt-3 border-t' : ''}">
				{#each fields as field (field.name)}
					<StageFieldRow
						{field}
						stageName={stage.name}
						value={launch.effective[stage.name]?.[field.name]}
						onChange={(value) => launch.setStageField(stage.name, field.name, value)}
					/>
				{/each}
			</div>
		{/if}
	</Popover.Content>
</Popover.Root>
