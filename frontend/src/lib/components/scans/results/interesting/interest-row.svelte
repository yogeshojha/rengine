<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Sparkle from '@lucide/svelte/icons/sparkle';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import CopyButton from '$lib/components/copy-button.svelte';
	import { BAND_RAIL } from '$lib/config/interest';
	import { INTEREST_SOURCE, type InterestRow } from '$lib/types/interest';
	import { stopProp } from '$lib/utilities';
	import SignalChip from './signal-chip.svelte';

	interface Props {
		row: InterestRow;
		rank: number;
		onOpen: (row: InterestRow) => void;
		onKind: (kind: string) => void;
		onDismiss: (row: InterestRow) => void;
		onHost: (host: string) => void;
	}

	let { row, rank, onOpen, onKind, onDismiss, onHost }: Props = $props();

	const MAX_CHIPS = 4;
	// the primary judgement or rule carries the sentence; the rest are chips only
	let lead = $derived(row.signals.find((s) => s.reason) ?? null);
	let chips = $derived(row.signals.slice(0, MAX_CHIPS));
	let rest = $derived(Math.max(0, row.signals.length - MAX_CHIPS));
	let fromAi = $derived(row.sources.includes(INTEREST_SOURCE.AI));
	let statusTone = $derived(
		row.http_status == null
			? 'text-muted-foreground'
			: row.http_status < 300
				? 'text-success'
				: row.http_status < 400
					? 'text-info'
					: 'text-warning'
	);
</script>

<div
	class="group flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-accent/40"
	role="button"
	tabindex={0}
	onclick={() => onOpen(row)}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onOpen(row);
		}
	}}
>
	<span class="flex h-5 shrink-0 items-center gap-2">
		<span class="h-4 w-0.5 rounded-full {BAND_RAIL[row.band] ?? 'bg-border'}"></span>
		<span class="w-5 text-right text-xs tabular-nums text-muted-foreground group-hover:hidden"
			>{rank}</span
		>
		<ArrowUpRight class="hidden size-3.5 w-5 text-primary group-hover:block" />
	</span>

	<div class="flex min-w-0 flex-1 flex-col gap-1.5">
		<div class="flex flex-wrap items-center gap-x-2.5 gap-y-1">
			<span class="font-mono text-[12.5px] font-medium wrap-anywhere">{row.host}</span>
			{#if row.http_status != null}
				<span class="text-[11px] tabular-nums {statusTone}">{row.http_status}</span>
			{/if}
			{#if row.tech.length}
				<span class="flex items-center gap-1 text-xs text-muted-foreground">
					<TechIcon name={row.tech[0]} class="size-3" />
					{row.tech[0]}
				</span>
			{/if}
			{#if row.is_new}
				<span
					class="rounded border border-primary/25 bg-primary/5 px-1 py-px text-[10px] text-primary"
					>New</span
				>
			{/if}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<span class="hidden group-hover:inline-flex" onclick={stopProp}>
				<CopyButton value={row.host} class="size-5" />
			</span>
		</div>

		{#if lead?.reason}
			<p class="max-w-[80ch] text-[12.5px] text-foreground/80">
				{#if fromAi && lead.source === INTEREST_SOURCE.AI}
					<Sparkle class="mr-1 inline size-3 align-[-1px] text-info" />
				{/if}{lead.reason}
			</p>
		{:else if row.page_title}
			<p class="max-w-[80ch] truncate text-[12.5px] text-muted-foreground">{row.page_title}</p>
		{/if}

		<div class="flex flex-wrap items-center gap-1">
			{#each chips as signal (signal.source + signal.kind)}
				<SignalChip {signal} onPick={onKind} />
			{/each}
			{#if rest > 0}
				<span class="rounded border border-border px-1.5 py-px text-[10px] text-muted-foreground"
					>+{rest}</span
				>
			{/if}
			{#if row.asn_org}
				<button
					type="button"
					class="text-[10px] text-muted-foreground hover:text-foreground"
					onclick={(e) => {
						e.stopPropagation();
						onHost(row.host);
					}}>{row.asn_org}</button
				>
			{/if}
		</div>
	</div>

	<span class="flex shrink-0 items-center gap-1 opacity-0 group-hover:opacity-100">
		<Hint text="Not interesting. Stays out on later scans of this target.">
			{#snippet child(props)}
				<Button
					{...props}
					variant="ghost"
					size="icon"
					class="size-7"
					onclick={(e) => {
						e.stopPropagation();
						onDismiss(row);
					}}
				>
					<X class="size-3.5" />
					<span class="sr-only">Dismiss {row.host}</span>
				</Button>
			{/snippet}
		</Hint>
	</span>
</div>
