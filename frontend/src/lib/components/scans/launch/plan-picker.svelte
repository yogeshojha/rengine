<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Select from '$lib/components/ui/select';
	import * as Tabs from '$lib/components/ui/tabs';
	import EffectPanel from '$lib/components/engines/effect-panel.svelte';
	import YamlPane from '$lib/components/engines/yaml-pane.svelte';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { ROUTES } from '$lib/config/routes';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import Hint from '$lib/components/hint.svelte';
	import {
		INTENSITIES,
		INTENSITY_HELP,
		INTENSITY_LABELS,
		type Intensity
	} from '$lib/types/scan-engine';
	import type { PreviewPhase } from '$lib/types/scan';
	import { relativeTime } from '$lib/utilities/dates';
	import { engineToYaml } from '$lib/utilities/engine-yaml';
	import { FOOTPRINT_LABEL, summarize } from '$lib/utilities/engine-summary';
	import { mostRecentEngine, type LaunchMode } from '$lib/utilities/launch-plan';
	import StagePill from './stage-pill.svelte';
	import StageConfigPopover from './stage-config-popover.svelte';
	import type { LaunchState } from './launch-state.svelte';

	interface Props {
		launch: LaunchState;
		phases: PreviewPhase[];
		phasesLoading: boolean;
		disabled?: boolean;
		onClose: () => void;
	}

	let { launch, phases, phasesLoading, disabled = false, onClose }: Props = $props();

	const MODES: { value: LaunchMode; label: string; caption: string }[] = [
		{
			value: 'engine',
			label: 'Scan Engine',
			caption: 'Runs a saved scan engine exactly as configured.'
		},
		{
			value: 'quick',
			label: 'Custom Scan',
			caption: 'Dependent stages are included automatically.'
		}
	];

	let view = $state<'pipeline' | 'yaml'>('pipeline');

	let engines = $derived(scanEnginesStore.engines);
	let groups = $derived(launch.catalog?.groups ?? []);
	let caption = $derived(
		launch.rescan
			? 'Runs against the chosen assets only. Dependent stages are included automatically.'
			: (MODES.find((m) => m.value === launch.mode)?.caption ?? '')
	);
	let allSelected = $derived(
		launch.quickStages.length > 0 &&
			launch.quickStages.every((s) => launch.effective[s.name]?.enabled)
	);
	let noneSelected = $derived(launch.quickStages.every((s) => !launch.effective[s.name]?.enabled));
	let yaml = $derived(
		launch.engine ? (launch.engine.yaml_source ?? engineToYaml(launch.engine, launch.catalog)) : ''
	);
	let engineSummary = $derived(
		launch.engine && launch.catalog
			? summarize(launch.engine.stages, launch.applicableStages, launch.engine.intensity)
			: null
	);

	function configurable(stageName: string): boolean {
		const stage = launch.catalog?.stages.find((s) => s.name === stageName);
		return !!stage && stage.fields.some((f) => f.name !== 'enabled');
	}

	function setMode(value: string) {
		if (value === 'engine' && launch.mode !== 'engine') {
			launch.applyEngine(launch.engineId ?? mostRecentEngine(engines)?.id ?? null);
		} else if (value === 'quick' && launch.mode !== 'quick') {
			launch.useQuick();
		}
	}

	function setIntensity(value: string) {
		if (!value) return;
		const next = value as Intensity;
		launch.intensity = next === launch.baseIntensity ? null : next;
	}

	function createEngine() {
		onClose();
		goto(ROUTES.engines);
	}
</script>

<div class="flex flex-col gap-3">
	<Label>{launch.rescan ? 'What to re-run' : 'Configuration'}</Label>
	{#if !launch.rescan}
		<Tabs.Root value={launch.mode} onValueChange={setMode} class="gap-3">
			<Tabs.List class="grid h-9 w-full grid-cols-2">
				{#each MODES as mode (mode.value)}
					<Tabs.Trigger value={mode.value} class="text-[13px]" {disabled}>
						{mode.label}
					</Tabs.Trigger>
				{/each}
			</Tabs.List>
		</Tabs.Root>
	{/if}

	{#if !launch.catalog}
		<div class="flex flex-col gap-3">
			{#each Array(4) as _, i (i)}
				<Skeleton class="h-7 w-full rounded-md" />
			{/each}
		</div>
	{:else if launch.mode === 'engine'}
		{#if engines.length === 0}
			<div
				class="flex items-center justify-between gap-3 rounded-md border border-dashed px-3 py-3 text-xs text-muted-foreground"
			>
				<span>No scan engines in this project.</span>
				<Button variant="outline" size="sm" class="h-7 text-xs" onclick={createEngine}>
					Create scan engine
				</Button>
			</div>
		{:else}
			<div class="flex flex-col gap-1.5">
				<div class="flex items-center gap-2">
					<Select.Root
						type="single"
						value={launch.engineId ?? ''}
						onValueChange={(v) => v && launch.applyEngine(v)}
						{disabled}
					>
						<Select.Trigger class="w-full sm:w-80" aria-label="Scan engine">
							{launch.engine?.name ?? 'Select a scan engine'}
						</Select.Trigger>
						<Select.Content>
							{#each engines as engine (engine.id)}
								<Select.Item value={engine.id} label={engine.name}>{engine.name}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
					{#if launch.engineId}
						<Button
							href={ROUTES.engine(launch.engineId)}
							target="_blank"
							rel="noopener noreferrer"
							variant="ghost"
							size="sm"
							class="h-9 gap-1 text-xs text-muted-foreground"
						>
							Open in editor <ArrowUpRight class="size-3.5" />
						</Button>
					{/if}
				</div>
				{#if launch.engine && engineSummary}
					<p class="text-[11px] text-muted-foreground">
						{INTENSITY_LABELS[launch.engine.intensity]} intensity · {engineSummary.activeStages} of
						{engineSummary.totalStages} stages · {FOOTPRINT_LABEL[engineSummary.footprint]}
						{#if launch.engine.last_used_at}
							· Last used {relativeTime(launch.engine.last_used_at)}
						{/if}
					</p>
				{:else}
					<p class="text-[11px] text-muted-foreground">{caption}</p>
				{/if}
			</div>
			{#if launch.engine}
				{#if launch.engine.description}
					<p class="text-xs text-muted-foreground">{launch.engine.description}</p>
				{/if}
				<Tabs.Root bind:value={view} class="gap-2">
					<Tabs.List class="h-8">
						<Tabs.Trigger value="pipeline" class="px-3 text-xs">Pipeline</Tabs.Trigger>
						<Tabs.Trigger value="yaml" class="px-3 text-xs">YAML Config</Tabs.Trigger>
					</Tabs.List>
					<Tabs.Content value="pipeline">
						<div class="h-80 overflow-hidden rounded-md border bg-card">
							<EffectPanel
								{phases}
								stages={launch.catalog.stages}
								isLoading={phasesLoading}
								error={null}
							/>
						</div>
					</Tabs.Content>
					<Tabs.Content value="yaml">
						<div class="h-80 overflow-hidden rounded-md border bg-card">
							<YamlPane value={yaml} readonly chrome={false} />
						</div>
					</Tabs.Content>
				</Tabs.Root>
			{/if}
		{/if}
	{:else}
		<div class="-mt-1 flex items-center justify-between gap-2">
			<p class="text-xs text-muted-foreground">{caption}</p>
			<div class="flex shrink-0 items-center gap-1">
				<Button
					variant="ghost"
					size="sm"
					class="h-6 px-2 text-xs text-muted-foreground"
					onclick={() => launch.selectAll()}
					disabled={disabled || allSelected}
				>
					Select all
				</Button>
				<Button
					variant="ghost"
					size="sm"
					class="h-6 px-2 text-xs text-muted-foreground"
					onclick={() => launch.clearAll()}
					disabled={disabled || noneSelected}
				>
					Clear selection
				</Button>
			</div>
		</div>
		<div class="flex flex-col gap-3">
			{#each groups as group (group.key)}
				{@const stages = launch.quickStages.filter((s) => s.group === group.key)}
				{#if stages.length}
					<div class="flex flex-col gap-1.5">
						<span class="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
							{group.label}
						</span>
						<div class="flex flex-wrap gap-1.5">
							{#each stages as stage (stage.name)}
								<StagePill
									{stage}
									state={launch.stageState(stage.name)}
									{disabled}
									onToggle={() => launch.toggleStage(stage.name)}
								>
									{#if configurable(stage.name)}
										<StageConfigPopover {stage} {launch} />
									{/if}
								</StagePill>
							{/each}
						</div>
					</div>
				{/if}
			{/each}
		</div>
		<div class="flex items-start justify-between gap-4 border-t pt-3">
			<div class="min-w-0">
				<Label class="text-[13px]">Intensity</Label>
				<p class="text-[11px] text-muted-foreground">{INTENSITY_HELP[launch.runIntensity]}</p>
			</div>
			<ToggleGroup.Root
				type="single"
				variant="outline"
				size="sm"
				value={launch.runIntensity}
				onValueChange={setIntensity}
				aria-label="Intensity"
				class="shrink-0"
				{disabled}
			>
				{#each INTENSITIES as level (level)}
					<Hint text={INTENSITY_HELP[level]}>
						{#snippet child(props)}
							<ToggleGroup.Item
								{...props}
								value={level}
								class="h-7 px-2.5 text-xs data-[state=on]:bg-foreground data-[state=on]:text-background dark:data-[state=on]:bg-foreground dark:data-[state=on]:text-background"
							>
								{INTENSITY_LABELS[level]}
							</ToggleGroup.Item>
						{/snippet}
					</Hint>
				{/each}
			</ToggleGroup.Root>
		</div>
	{/if}
</div>
