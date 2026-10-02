<script module lang="ts">
	export interface RailRow {
		key: string;
		label: string;
		help: string;
		failing: number;
		share: number;
		shareLabel: string;
	}

	export interface RailBreakdown {
		warnings: RailRow[];
		infos: RailRow[];
		evaluated: number;
		pending: number;
	}
</script>

<script lang="ts">
	import X from '@lucide/svelte/icons/x';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import { HygieneTone } from '$lib/config/hygiene';
	import type { HygieneSummary } from '$lib/utilities/scan-insights';
	import { plural } from '$lib/utilities/strings';

	interface Props {
		label: string;
		summary: HygieneSummary | null;
		breakdown: RailBreakdown;
		evaluatedLabel: string;
		pendingLabel: string;
		emptyText?: string;
		noneKey: string;
		toneDot: Record<HygieneTone, string>;
		toneLabel: Record<HygieneTone, string>;
		selected: string[];
		onToggle: (key: string) => void;
		onClose: () => void;
	}

	let {
		label,
		summary,
		breakdown,
		evaluatedLabel,
		pendingLabel,
		emptyText,
		noneKey,
		toneDot,
		toneLabel,
		selected,
		onToggle,
		onClose
	}: Props = $props();

	const MIN_METER = 1.5;

	let cleanOn = $derived(selected.includes(noneKey));
	let pendingLine = $derived(`${plural(breakdown.pending, 'web asset')} ${pendingLabel}`);
</script>

<aside
	class="order-first flex w-full shrink-0 flex-col border-b bg-card md:sticky md:top-[calc(var(--scan-tabs-h,0px)+4rem)] md:order-last md:w-80 md:self-start md:border-b-0 md:border-l"
	aria-label={label}
>
	<div class="flex h-10 items-center gap-2 border-b px-4">
		<span class="text-sm font-medium">{label}</span>
		{#if summary}
			<span class="text-xs text-muted-foreground tabular-nums">
				{breakdown.evaluated.toLocaleString()}
				{evaluatedLabel}
			</span>
		{/if}
		<Button
			variant="ghost"
			size="icon"
			class="ml-auto size-7 text-muted-foreground"
			aria-label="Close {label.toLowerCase()}"
			onclick={onClose}
		>
			<X class="size-4" />
		</Button>
	</div>

	{#if !summary}
		<div class="flex flex-col gap-3 p-4">
			{#each Array(6) as _, i (i)}
				<Skeleton class="h-8 w-full" />
			{/each}
		</div>
	{:else if breakdown.evaluated === 0}
		<p class="p-4 text-xs text-muted-foreground">{emptyText ?? `${pendingLine}.`}</p>
	{:else}
		{@render section(HygieneTone.WARNING, breakdown.warnings)}
		{@render section(HygieneTone.INFO, breakdown.infos)}
		<div class="flex flex-col gap-1.5 border-t px-4 py-3 text-xs text-muted-foreground">
			{#if summary.clean > 0}
				<button
					type="button"
					class="flex items-center gap-1 text-left text-primary hover:text-primary/80 {cleanOn
						? 'font-medium'
						: ''}"
					aria-pressed={cleanOn}
					onclick={() => onToggle(noneKey)}
				>
					{plural(summary.clean, 'web asset passes', 'web assets pass')} every applicable check
					<ChevronRight class="size-3.5" />
				</button>
			{/if}
			{#if breakdown.pending > 0}
				<span class="tabular-nums">{pendingLine}</span>
			{/if}
		</div>
	{/if}
</aside>

{#snippet section(tone: HygieneTone, rows: RailRow[])}
	<section class="flex flex-col px-2 pt-3 pb-1">
		<div class="flex items-center gap-2 px-2 pb-1.5 text-xs">
			<span class="size-1.5 rounded-full {toneDot[tone]}" aria-hidden="true"></span>
			<span class="font-medium">{toneLabel[tone]}</span>
			<span class="ml-auto text-muted-foreground tabular-nums">
				{plural(rows.length, 'check')}
			</span>
		</div>
		{#if rows.length}
			<ul class="flex flex-col">
				{#each rows as r (r.key)}
					{@const on = selected.includes(r.key)}
					<li>
						<button
							type="button"
							class="flex w-full flex-col gap-1 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-muted/50 {on
								? 'bg-muted'
								: ''}"
							aria-pressed={on}
							onclick={() => onToggle(r.key)}
						>
							<span class="flex w-full items-baseline gap-2">
								<Hint text={r.help}>
									{#snippet child(props)}
										<span {...props} class="min-w-0 flex-1 truncate text-xs leading-4"
											>{r.label}</span
										>
									{/snippet}
								</Hint>
								<span class="text-xs font-medium tabular-nums">{r.failing.toLocaleString()}</span>
								<span class="w-8 shrink-0 text-right text-2xs text-muted-foreground tabular-nums">
									{r.shareLabel}
								</span>
							</span>
							<span
								class="block h-0.5 w-full overflow-hidden rounded-full {on
									? 'bg-card'
									: 'bg-muted'}"
								aria-hidden="true"
							>
								<span
									class="block h-full rounded-full {toneDot[tone]}"
									style="width:{Math.max(MIN_METER, r.share)}%"
								></span>
							</span>
						</button>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="px-2 pb-1 text-xs text-muted-foreground">
				No {toneLabel[tone].toLowerCase()} checks failing.
			</p>
		{/if}
	</section>
{/snippet}
