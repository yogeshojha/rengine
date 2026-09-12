<script lang="ts">
	import X from '@lucide/svelte/icons/x';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import {
		HYGIENE_NONE,
		HygieneTone,
		TONE_DOT,
		TONE_LABEL,
		hygieneBreakdown,
		hygieneShare,
		hygieneShareLabel,
		type HygieneRow
	} from '$lib/config/hygiene';
	import type { HygieneSummary } from '$lib/utilities/scan-insights';

	interface Props {
		summary: HygieneSummary | null;
		selected: string[];
		onToggle: (key: string) => void;
		onClose: () => void;
	}

	let { summary, selected, onToggle, onClose }: Props = $props();

	const MIN_METER = 1.5;
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	let breakdown = $derived(hygieneBreakdown(summary));
	let cleanOn = $derived(selected.includes(HYGIENE_NONE));
</script>

<aside
	class="order-first flex w-full shrink-0 flex-col border-b bg-card md:sticky md:top-[calc(var(--scan-tabs-h,0px)+4rem)] md:order-last md:w-80 md:self-start md:border-b-0 md:border-l"
	aria-label="Web hygiene"
>
	<div class="flex h-10 items-center gap-2 border-b px-4">
		<span class="text-sm font-medium">Web hygiene</span>
		{#if summary}
			<span class="text-xs text-muted-foreground tabular-nums">
				{breakdown.evaluated.toLocaleString()} checked
			</span>
		{/if}
		<Button
			variant="ghost"
			size="icon"
			class="ml-auto size-7 text-muted-foreground"
			aria-label="Close web hygiene"
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
		<p class="p-4 text-xs text-muted-foreground">
			{plural(breakdown.pending, 'web asset', 'web assets')} pending evaluation.
		</p>
	{:else}
		{@render section(HygieneTone.WARNING, breakdown.warnings)}
		{@render section(HygieneTone.INFO, breakdown.infos)}
		<div class="flex flex-col gap-1.5 border-t px-4 py-3 text-xs text-muted-foreground">
			{#if summary.clean > 0}
				<button
					type="button"
					class="flex items-center gap-1 text-left text-primary hover:underline {cleanOn
						? 'font-medium'
						: ''}"
					aria-pressed={cleanOn}
					onclick={() => onToggle(HYGIENE_NONE)}
				>
					{plural(summary.clean, 'web asset passes', 'web assets pass')} every applicable check
					<ChevronRight class="size-3.5" />
				</button>
			{/if}
			{#if breakdown.pending > 0}
				<span class="tabular-nums"
					>{plural(breakdown.pending, 'web asset', 'web assets')} pending evaluation</span
				>
			{/if}
		</div>
	{/if}
</aside>

{#snippet section(tone: HygieneTone, rows: HygieneRow[])}
	<section class="flex flex-col px-2 pt-3 pb-1">
		<div class="flex items-center gap-2 px-2 pb-1.5 text-xs">
			<span class="size-1.5 rounded-full {TONE_DOT[tone]}" aria-hidden="true"></span>
			<span class="font-medium">{TONE_LABEL[tone]}</span>
			<span class="ml-auto text-muted-foreground tabular-nums">
				{plural(rows.length, 'check', 'checks')}
			</span>
		</div>
		{#if rows.length}
			<ul class="flex flex-col">
				{#each rows as r (r.spec.key)}
					{@const on = selected.includes(r.spec.key)}
					<li>
						<button
							type="button"
							class="flex w-full flex-col gap-1 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-muted/50 {on
								? 'bg-muted'
								: ''}"
							aria-pressed={on}
							onclick={() => onToggle(r.spec.key)}
						>
							<span class="flex w-full items-baseline gap-2">
								<Hint text={r.spec.help}>
									{#snippet child(props)}
										<span {...props} class="min-w-0 flex-1 truncate text-xs leading-4"
											>{r.spec.label}</span
										>
									{/snippet}
								</Hint>
								<span class="text-xs font-medium tabular-nums"
									>{r.count.failing.toLocaleString()}</span
								>
								<span class="w-8 shrink-0 text-right text-2xs text-muted-foreground tabular-nums">
									{hygieneShareLabel(r)}
								</span>
							</span>
							<span
								class="block h-0.5 w-full overflow-hidden rounded-full {on
									? 'bg-card'
									: 'bg-muted'}"
								aria-hidden="true"
							>
								<span
									class="block h-full rounded-full {TONE_DOT[tone]}"
									style="width:{Math.max(MIN_METER, hygieneShare(r))}%"
								></span>
							</span>
						</button>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="px-2 pb-1 text-xs text-muted-foreground">
				No {TONE_LABEL[tone].toLowerCase()} checks failing.
			</p>
		{/if}
	</section>
{/snippet}
