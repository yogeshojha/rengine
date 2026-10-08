<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Eye from '@lucide/svelte/icons/eye';
	import ScanEye from '@lucide/svelte/icons/scan-eye';
	import Sparkle from '@lucide/svelte/icons/sparkle';
	import X from '@lucide/svelte/icons/x';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as ScrollArea from '$lib/components/ui/scroll-area';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import CopyButton from '$lib/components/copy-button.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import NewBadge from '$lib/components/new-badge.svelte';
	import { SHEET_HEAD } from '../sheet';
	import SheetTop from '../sheet-top.svelte';
	import SheetBar from '../sheet-bar.svelte';
	import { BAND_TEXT, kindIcon, sourceChipClass } from '$lib/config/interest';
	import { interestCatalog } from '$lib/stores/interest-catalog.svelte';
	import { INTEREST_SOURCE, type InterestRow } from '$lib/types/interest';

	interface Props {
		row: InterestRow | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		onDismiss: (row: InterestRow) => void;
		onOpenAssets: (row: InterestRow) => void;
		/** where focus goes when the sheet closes; the table hands it to its cursor row */
		onCloseAutoFocus?: (e: Event) => void;
	}

	let { row, open, onOpenChange, onDismiss, onOpenAssets, onCloseAutoFocus }: Props = $props();

	let ordered = $derived(row ? [...row.signals].sort((a, b) => b.weight - a.weight) : []);
	let contentEl = $state<HTMLElement | null>(null);
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content
		bind:ref={contentEl}
		side="right"
		tabindex={-1}
		class="flex w-full flex-col gap-0 p-0 outline-none sm:max-w-lg"
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			contentEl?.focus();
		}}
		{onCloseAutoFocus}
	>
		{#if row}
			<Sheet.Header class={SHEET_HEAD}>
				<SheetTop noun="exposure">
					<span class="text-xs font-medium {BAND_TEXT[row.band] ?? ''}"
						>{interestCatalog.bandLabel(row.band)}</span
					>
					{#if row.http_status != null}
						<span class="font-mono text-xs text-muted-foreground tabular-nums"
							>{row.http_status}</span
						>
					{/if}
				</SheetTop>
				<div class="flex min-w-0 items-center gap-1">
					<Sheet.Title class="min-w-0 truncate font-mono text-base font-medium"
						>{row.host}</Sheet.Title
					>
					<CopyButton value={row.host} />
				</div>
				{#if row.tech.length || row.asn_org}
					<Sheet.Description class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
						{#if row.tech.length}
							<span class="flex min-w-0 items-center gap-1">
								<TechIcon name={row.tech[0]} class="size-3 shrink-0" />
								<span class="truncate">{row.tech.join(', ')}</span>
							</span>
						{/if}
						{#if row.asn_org}<span class="truncate">{row.asn_org}</span>{/if}
					</Sheet.Description>
				{/if}
				{#if row.is_cdn || row.is_new}
					<div class="flex flex-wrap gap-1">
						{#if row.is_cdn}<Badge variant="info" class="font-normal">CDN</Badge>{/if}
						{#if row.is_new}<NewBadge size="sm" />{/if}
					</div>
				{/if}
			</Sheet.Header>

			<SheetBar>
				<Button
					variant="outline"
					size="sm"
					onclick={() => {
						onDismiss(row);
						onOpenChange(false);
					}}
				>
					<X class="size-3.5" />
					Dismiss
				</Button>
				<Button size="sm" onclick={() => onOpenAssets(row)}>
					Open in Web assets
					<ArrowUpRight class="size-3.5" />
				</Button>
			</SheetBar>

			<ScrollArea.Root class="min-h-0 flex-1">
				<div class="flex flex-col gap-5 px-5 py-4">
					{#if ordered.length}
						<section class="flex flex-col gap-3">
							<SectionHead icon={ScanEye} title="Signals" />
							{#each ordered as signal (`${signal.source}:${signal.kind}:${signal.rule_id ?? ''}`)}
								{@const Icon = kindIcon(signal.kind)}
								{@const isAi = signal.source === INTEREST_SOURCE.AI}
								<div
									class="flex flex-col gap-1.5 border-l-2 pl-3 {isAi
										? 'border-info/50'
										: signal.source === INTEREST_SOURCE.CORRELATION
											? 'border-border'
											: 'border-primary/50'}"
								>
									<span class="flex flex-wrap items-center gap-2 text-xs font-medium">
										<Icon class="size-3.5 text-muted-foreground" />
										{signal.kind_label}
										<span
											class="rounded border px-1 py-px text-2xs font-normal {sourceChipClass(
												signal.source
											)}"
										>
											{isAi
												? 'AI judgement'
												: signal.label || interestCatalog.sourceLabel(signal.source)}
										</span>
									</span>
									{#if signal.reason}
										<p class="text-xs text-foreground/80">{signal.reason}</p>
									{:else}
										<p class="text-xs text-muted-foreground">
											{interestCatalog.kind(signal.kind)?.help ?? ''}
										</p>
									{/if}
									{#if isAi}
										<p class="flex items-center gap-1.5 text-2xs text-muted-foreground">
											<Sparkle class="size-3 text-info" />
											Written by {signal.model ?? 'a model'}.
										</p>
									{:else if signal.evidence}
										<p
											class="rounded border border-border bg-accent/40 p-2 font-mono text-2xs break-all text-muted-foreground"
										>
											{signal.evidence}
										</p>
									{/if}
								</div>
							{/each}
						</section>
					{/if}

					{#if row.page_title || row.resolved_ips.length}
						<section class="flex flex-col gap-2">
							<SectionHead icon={Eye} title="Observed" />
							{#if row.page_title}
								<p class="text-xs">{row.page_title}</p>
							{/if}
							{#if row.resolved_ips.length}
								<p class="font-mono text-2xs text-muted-foreground">
									{row.resolved_ips.join(', ')}
								</p>
							{/if}
						</section>
					{/if}
				</div>
			</ScrollArea.Root>
		{/if}
	</Sheet.Content>
</Sheet.Root>
