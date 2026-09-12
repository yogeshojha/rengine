<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Copy from '@lucide/svelte/icons/copy';
	import ImageOff from '@lucide/svelte/icons/image-off';
	import * as Sheet from '$lib/components/ui/sheet';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Kbd } from '$lib/components/ui/kbd';
	import Hint from '$lib/components/hint.svelte';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import VerbRail from './verb-rail.svelte';
	import { SIGNAL_TONE_CLASS, VERB, signalSpec } from '$lib/config/compare';
	import { surfaceSpec } from '$lib/config/surface';
	import { ROUTES } from '$lib/config/routes';
	import { screenshotUrl } from '$lib/utilities/media';
	import { durationText } from '$lib/utilities/scan-status';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { cn } from '$lib/utils';
	import { CHANGE_VERB, type ChangeRow, type RunSide } from '$lib/types/compare';

	interface Props {
		row: ChangeRow | null;
		baseline: RunSide;
		current: RunSide;
		open: boolean;
		index: number;
		total: number;
		onOpenChange: (open: boolean) => void;
		onStep: (dir: -1 | 1) => void;
	}

	let { row, baseline, current, open, index, total, onOpenChange, onStep }: Props = $props();

	let signal = $derived(row ? signalSpec(row.signal) : null);
	let verb = $derived(row ? VERB[row.verb] : null);
	let spec = $derived(row ? surfaceSpec(row.dimension) : undefined);
	let gone = $derived(
		row?.verb === CHANGE_VERB.DISAPPEARED || row?.verb === CHANGE_VERB.UNCONFIRMED
	);
	let appeared = $derived(row?.verb === CHANGE_VERB.APPEARED);
	let leftShot = $derived(screenshotUrl(row?.screenshots?.baseline));
	let rightShot = $derived(screenshotUrl(row?.screenshots?.current));
	let hasShots = $derived(Boolean(leftShot || rightShot));

	const when = (iso: string | null) =>
		iso
			? new Date(iso).toLocaleString('en-US', {
					month: 'short',
					day: 'numeric',
					hour: 'numeric',
					minute: '2-digit'
				})
			: '';
	const tabTarget = (dimension: string) => surfaceSpec(dimension)?.tab ?? 'overview';
</script>

{#snippet head(label: string, side: RunSide, absent: boolean)}
	<div class="flex min-w-0 flex-col gap-0.5">
		<span class="text-[10px] tracking-wider text-muted-foreground uppercase">{label}</span>
		<a
			href={ROUTES.scanTab(side.scan_id, tabTarget(row?.dimension ?? ''))}
			class="inline-flex items-center gap-1 truncate text-xs font-medium hover:text-primary"
		>
			{side.engine_name}
			<ArrowUpRight class="size-3 shrink-0" />
		</a>
		<span class="truncate text-[11px] text-muted-foreground tabular-nums">
			{[
				when(side.started_at),
				side.duration_seconds != null ? durationText(side.duration_seconds) : ''
			]
				.filter(Boolean)
				.join(' · ')}
		</span>
		{#if absent}
			<span class="text-[11px] text-muted-foreground">Not present</span>
		{/if}
	</div>
{/snippet}

<Sheet.Root {open} onOpenChange={(v) => onOpenChange(v)}>
	<Sheet.Content
		side="right"
		class="flex w-full flex-col gap-0 p-0 sm:max-w-[42rem]"
		aria-describedby={undefined}
	>
		{#if row && signal && verb}
			<Sheet.Header class="gap-2 border-b px-5 py-4 pr-12">
				<div class="flex flex-wrap items-center gap-2">
					<VerbRail verb={row.verb} size="dot" />
					<Badge variant="outline" class="h-5 px-2 text-[10px]">{verb.label}</Badge>
					<span
						class={cn(
							'flex items-center gap-1.5 text-xs font-medium',
							SIGNAL_TONE_CLASS[signal.tone]
						)}
					>
						<signal.icon class="size-3.5" />
						{signal.label}
					</span>
					{#if spec}
						<span class="flex items-center gap-1.5 text-xs text-muted-foreground">
							<span class="opacity-40">·</span>
							<spec.icon class="size-3.5" />
							{spec.label}
						</span>
					{/if}
				</div>

				<Sheet.Title class="flex min-w-0 items-start gap-2 font-mono text-sm break-all">
					{#if row.severity}
						<SeverityMark severity={row.severity} class="mt-0.5 shrink-0" />
					{/if}
					<span class="min-w-0">{row.title}</span>
					<Hint text="Copy">
						{#snippet child(props)}
							<Button
								{...props}
								variant="ghost"
								size="icon-sm"
								class="size-6 shrink-0"
								onclick={() => writeClipboard(row?.title ?? '')}
							>
								<Copy class="size-3" />
							</Button>
						{/snippet}
					</Hint>
				</Sheet.Title>

				{#if row.subtitle}
					<p class="truncate text-xs text-muted-foreground">{row.subtitle}</p>
				{/if}

				<div class="flex items-center gap-2 pt-1">
					<span class="text-xs text-muted-foreground tabular-nums">
						{index + 1} of {total.toLocaleString()}
					</span>
					<div class="ml-auto flex items-center gap-1">
						<Hint text="Previous change">
							{#snippet child(props)}
								<Button
									{...props}
									variant="outline"
									size="icon-sm"
									class="size-7"
									disabled={index <= 0}
									onclick={() => onStep(-1)}
								>
									<ChevronUp class="size-3.5" />
								</Button>
							{/snippet}
						</Hint>
						<Hint text="Next change">
							{#snippet child(props)}
								<Button
									{...props}
									variant="outline"
									size="icon-sm"
									class="size-7"
									disabled={index >= total - 1}
									onclick={() => onStep(1)}
								>
									<ChevronDown class="size-3.5" />
								</Button>
							{/snippet}
						</Hint>
						<Kbd class="hidden sm:inline-flex">j</Kbd>
						<Kbd class="hidden sm:inline-flex">k</Kbd>
					</div>
				</div>
			</Sheet.Header>

			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col">
					<div class="grid grid-cols-2 gap-4 border-b px-5 py-3.5">
						{@render head('Baseline', baseline, appeared)}
						{@render head('Current', current, gone)}
					</div>

					{#if hasShots}
						<div class="grid grid-cols-2 gap-4 border-b px-5 py-4">
							{#each [leftShot, rightShot] as shot, i (i)}
								{#if shot}
									<img
										src={shot}
										alt={i === 0 ? 'baseline screenshot' : 'current screenshot'}
										loading="lazy"
										class="aspect-[16/10] w-full rounded-md border object-cover object-top"
									/>
								{:else}
									<div
										class="flex aspect-[16/10] w-full items-center justify-center rounded-md border border-dashed text-muted-foreground"
									>
										<ImageOff class="size-4" />
									</div>
								{/if}
							{/each}
						</div>
					{/if}

					{#if row.fields.length}
						<dl
							class="grid grid-cols-[minmax(0,7.5rem)_minmax(0,1fr)_minmax(0,1fr)] items-baseline"
						>
							<div class="col-span-3 grid grid-cols-subgrid border-b bg-muted/30 px-5 py-1.5">
								<span></span>
								<span class="text-[10px] tracking-wider text-muted-foreground uppercase">Was</span>
								<span class="text-[10px] tracking-wider text-muted-foreground uppercase">Now</span>
							</div>
							{#each row.fields as f (f.field)}
								<div
									class="col-span-3 grid grid-cols-subgrid gap-x-4 border-b px-5 py-2 last:border-b-0"
								>
									<dt class="text-xs text-muted-foreground">{f.label}</dt>
									<dd class="m-0 font-mono text-xs break-all text-muted-foreground">
										{f.before ?? '—'}
									</dd>
									<dd class="m-0 font-mono text-xs break-all">
										<span class="rounded bg-primary/10 px-1 font-medium">{f.after ?? '—'}</span>
									</dd>
								</div>
							{/each}
						</dl>
					{:else}
						<p class="px-5 py-4 text-xs text-muted-foreground">
							{gone
								? 'Present in the baseline run, absent in the current one.'
								: appeared
									? 'Absent from the baseline run.'
									: 'Identity only. No watched field differs.'}
						</p>
					{/if}
				</div>
			</ScrollArea>

			<div class="flex flex-wrap items-center gap-2 border-t px-5 py-3">
				<Button
					variant="outline"
					size="sm"
					href={ROUTES.scanTab(row.scan_id, tabTarget(row.dimension))}
					class="gap-1.5"
				>
					Open in results <ArrowUpRight class="size-3.5" />
				</Button>
				<span class="text-xs text-muted-foreground">
					{gone ? 'Last seen in the baseline run' : 'Recorded by the current run'}
				</span>
			</div>
		{/if}
	</Sheet.Content>
</Sheet.Root>
