<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Badge, type BadgeVariant } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Separator } from '$lib/components/ui/separator';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import Play from '@lucide/svelte/icons/play';
	import Copy from '@lucide/svelte/icons/copy';
	import Download from '@lucide/svelte/icons/download';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import MoreHorizontal from '@lucide/svelte/icons/more-horizontal';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import StageList from './stage-list.svelte';
	import FootprintMeter from './footprint-meter.svelte';
	import type { Intensity, ScanEngine, StageCatalogEntry } from '$lib/types/scan-engine';
	import { INTENSITY_LABELS } from '$lib/types/scan-engine';
	import { summarize } from '$lib/utilities/engine-summary';
	import { formatDistanceToNow } from '$lib/utilities/dates';

	interface Props {
		engine: ScanEngine;
		stages: StageCatalogEntry[];
		isSelected?: boolean;
		onSelect?: () => void;
		onEdit?: () => void;
		onRun?: () => void;
		onDuplicate?: () => void;
		onExport?: () => void;
		onDelete?: () => void;
	}

	let {
		engine,
		stages,
		isSelected = false,
		onSelect,
		onEdit,
		onRun,
		onDuplicate,
		onExport,
		onDelete
	}: Props = $props();

	const INTENSITY_VARIANT: Record<Intensity, BadgeVariant> = {
		passive: 'outline',
		normal: 'secondary',
		aggressive: 'warning'
	};

	const summary = $derived(summarize(engine.stages ?? {}, stages, engine.intensity));

	const keyedStages = $derived(
		stages.filter(
			(s) => s.api_keys.length && Boolean(engine.stages?.[s.name]?.enabled ?? s.defaults.enabled)
		)
	);
	const keyNames = $derived([...new Set(keyedStages.flatMap((s) => s.api_keys))]);

	const usage = $derived.by(() => {
		const parts: string[] = [];
		const scans = engine.usage?.scans ?? 0;
		if (scans) parts.push(`${scans} scan${scans === 1 ? '' : 's'}`);
		if (engine.last_used_at) parts.push(`used ${formatDistanceToNow(engine.last_used_at)}`);
		return parts.length ? parts.join(' · ') : 'Never used';
	});
</script>

<Card.Root
	class="group relative gap-0 py-0 transition-colors hover:border-foreground/25 data-[selected=true]:border-primary/50 data-[selected=true]:bg-primary/5"
	data-selected={isSelected}
>
	<div class="flex items-start gap-3 px-4 pt-4">
		{#if onSelect}
			<div
				class="relative z-10 flex h-5 items-center opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100 data-[on=true]:opacity-100 [@media(hover:none)]:opacity-100"
				data-on={isSelected}
			>
				<Checkbox
					checked={isSelected}
					onCheckedChange={() => onSelect()}
					aria-label="Select {engine.name}"
				/>
			</div>
		{/if}

		<div class="min-w-0 flex-1">
			<div class="flex flex-wrap items-center gap-2">
				<button
					type="button"
					class="truncate text-left text-sm font-semibold after:absolute after:inset-0 after:rounded-xl focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-ring"
					onclick={() => onEdit?.()}
				>
					{engine.name}
				</button>
				<Badge variant={INTENSITY_VARIANT[engine.intensity] ?? 'secondary'} class="text-[10px]">
					{INTENSITY_LABELS[engine.intensity] ?? engine.intensity}
				</Badge>
			</div>
			{#if engine.description}
				<p class="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{engine.description}</p>
			{/if}
		</div>

		<div class="relative z-10 -mt-1 -mr-2 flex items-center">
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="icon-sm"
							class="text-muted-foreground"
							aria-label="More actions for {engine.name}"
						>
							<MoreHorizontal size={15} />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-44">
					<DropdownMenu.Item onclick={() => onDuplicate?.()}>
						<Copy size={13} />
						Duplicate
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={() => onExport?.()}>
						<Download size={13} />
						Export YAML
					</DropdownMenu.Item>
					<DropdownMenu.Separator />
					<DropdownMenu.Item variant="destructive" onclick={() => onDelete?.()}>
						<Trash2 size={13} />
						Delete
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>

	<div class="px-4 pt-4">
		<StageList {stages} config={engine.stages ?? {}} intensity={engine.intensity} />
	</div>

	<div class="mt-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 px-4 text-xs">
		<FootprintMeter footprint={summary.footprint} requestsPerSecond={summary.requestsPerSecond} />
		{#if keyNames.length}
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<span
							{...props}
							class="relative z-10 inline-flex items-center gap-1.5 text-muted-foreground"
						>
							<KeyRound size={12} />
							{keyNames.length} API key{keyNames.length === 1 ? '' : 's'}
						</span>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content class="text-xs">Uses {keyNames.join(', ')}</Tooltip.Content>
			</Tooltip.Root>
		{/if}
	</div>

	<Separator class="mt-4" />

	<div class="flex items-center justify-between gap-3 px-4 py-2">
		<span class="flex min-w-0 items-center gap-1.5 truncate text-[11px] text-muted-foreground">
			{#if engine.usage?.schedules}
				<CalendarClock size={12} class="shrink-0" />
				{engine.usage.schedules} schedule{engine.usage.schedules === 1 ? '' : 's'}
				<span aria-hidden="true">·</span>
			{/if}
			{usage}
		</span>
		<Button
			variant="ghost"
			size="sm"
			class="relative z-10 h-7 gap-1.5 px-2 text-xs"
			onclick={() => onRun?.()}
		>
			<Play size={12} />
			Run
		</Button>
	</div>
</Card.Root>
