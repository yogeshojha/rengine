<script lang="ts">
	import * as Select from '$lib/components/ui/select';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { Separator } from '$lib/components/ui/separator';
	import { Spinner } from '$lib/components/ui/spinner';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Wrench from '@lucide/svelte/icons/wrench';
	import FootprintMeter from './footprint-meter.svelte';
	import { footprintFor } from '$lib/utilities/engine-summary';
	import { targetTypeLabel, type StageCatalogEntry } from '$lib/types/scan-engine';
	import type { PreviewPhase } from '$lib/types/scan';

	interface Props {
		targetType: string;
		targetTypes: string[];
		phases: PreviewPhase[];
		warnings: string[];
		stages: StageCatalogEntry[];
		isLoading: boolean;
		error: string | null;
		onTargetTypeChange: (value: string) => void;
	}

	let {
		targetType,
		targetTypes,
		phases,
		warnings,
		stages,
		isLoading,
		error,
		onTargetTypeChange
	}: Props = $props();

	const MAX_TOOLS = 6;

	const tools = $derived(phases.flatMap((p) => p.tools));
	const running = $derived(tools.filter((t) => t.status === 'will_run'));
	const requestsPerSecond = $derived(running.reduce((n, t) => n + (t.rate ?? 0), 0));
	const runningSpecs = $derived(
		running
			.map((t) => stages.find((s) => s.name === t.capability))
			.filter((s): s is StageCatalogEntry => Boolean(s))
	);
	const touchesTarget = $derived(runningSpecs.some((s) => s.touches_target));
	const footprint = $derived(footprintFor(requestsPerSecond, touchesTarget));
	const toolNames = $derived([...new Set(runningSpecs.flatMap((s) => s.tools))].sort());
	const hidden = $derived(Math.max(0, toolNames.length - MAX_TOOLS));
</script>

<div class="bar">
	<span class="lens">
		<span class="dim">Against a</span>
		<Select.Root type="single" value={targetType} onValueChange={(v) => v && onTargetTypeChange(v)}>
			<Select.Trigger
				class="h-6 w-auto min-w-[88px] gap-1 border-0 bg-muted px-2 text-xs font-medium shadow-none"
				aria-label="Preview target type"
			>
				{targetTypeLabel(targetType)}
			</Select.Trigger>
			<Select.Content>
				{#each targetTypes as type (type)}
					<Select.Item value={type} label={targetTypeLabel(type)}>
						{targetTypeLabel(type)}
					</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		<span class="dim">target</span>
	</span>

	<Separator orientation="vertical" class="hidden data-[orientation=vertical]:h-4 sm:block" />

	{#if error}
		<span class="text-destructive">{error}</span>
	{:else if isLoading && !phases.length}
		<Spinner size={12} class="text-muted-foreground" />
	{:else}
		<span class="stat">
			<strong>{running.length}</strong>
			<span class="dim">of {tools.length} stages run</span>
		</span>

		<FootprintMeter {footprint} {requestsPerSecond} />

		{#if toolNames.length}
			<span class="tools">
				<Wrench size={12} class="shrink-0 text-muted-foreground" />
				{#each toolNames.slice(0, MAX_TOOLS) as tool (tool)}
					<span class="tool">{tool}</span>
				{/each}
				{#if hidden}
					<HoverCard.Root openDelay={100}>
						<HoverCard.Trigger>
							{#snippet child({ props })}
								<span {...props} class="tool more">+{hidden}</span>
							{/snippet}
						</HoverCard.Trigger>
						<HoverCard.Content class="w-auto max-w-xs p-3 text-xs">
							<p class="mb-1.5 font-medium">All tools</p>
							<p class="font-mono text-[11px] leading-relaxed text-muted-foreground">
								{toolNames.join(' · ')}
							</p>
						</HoverCard.Content>
					</HoverCard.Root>
				{/if}
			</span>
		{/if}

		{#if warnings.length}
			<HoverCard.Root openDelay={100}>
				<HoverCard.Trigger>
					{#snippet child({ props })}
						<span {...props} class="warn">
							<TriangleAlert size={12} />
							{warnings.length} warning{warnings.length === 1 ? '' : 's'}
						</span>
					{/snippet}
				</HoverCard.Trigger>
				<HoverCard.Content class="w-80 p-3 text-xs">
					<ul class="space-y-1.5">
						{#each warnings as warning (warning)}
							<li class="flex gap-2">
								<TriangleAlert size={12} class="mt-0.5 shrink-0 text-warning" />
								<span>{warning}</span>
							</li>
						{/each}
					</ul>
				</HoverCard.Content>
			</HoverCard.Root>
		{/if}

		{#if isLoading}
			<Spinner size={11} class="text-muted-foreground" />
		{/if}
	{/if}
</div>

<style>
	.bar {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 6px 14px;
		flex-shrink: 0;
		min-height: 36px;
		padding: 5px 16px;
		border-bottom: 1px solid var(--border);
		background: color-mix(in oklch, var(--muted) 45%, var(--background));
		font-size: 12px;
	}
	.lens {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.dim {
		color: var(--muted-foreground);
	}
	.stat {
		display: inline-flex;
		align-items: baseline;
		gap: 4px;
		font-variant-numeric: tabular-nums;
	}
	.stat strong {
		font-weight: 600;
	}
	.tools {
		display: inline-flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 4px;
		min-width: 0;
	}
	.tool {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 10.5px;
		line-height: 18px;
		padding: 0 6px;
		border-radius: 4px;
		background: var(--muted);
		color: var(--muted-foreground);
	}
	.tool.more {
		cursor: default;
		color: var(--foreground);
	}
	@media (max-width: 640px) {
		.tools {
			display: none;
		}
	}
	.warn {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: var(--warning);
		cursor: default;
	}
</style>
