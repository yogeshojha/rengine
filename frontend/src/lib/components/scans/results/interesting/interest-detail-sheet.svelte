<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Sparkle from '@lucide/svelte/icons/sparkle';
	import X from '@lucide/svelte/icons/x';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as ScrollArea from '$lib/components/ui/scroll-area';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import CopyButton from '$lib/components/copy-button.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import { BAND_TEXT, kindIcon, sourceChipClass } from '$lib/config/interest';
	import { interestCatalog } from '$lib/stores/interest-catalog.svelte';
	import { INTEREST_SOURCE, type InterestRow } from '$lib/types/interest';

	interface Props {
		row: InterestRow | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		onDismiss: (row: InterestRow) => void;
		onOpenAssets: (row: InterestRow) => void;
	}

	let { row, open, onOpenChange, onDismiss, onOpenAssets }: Props = $props();

	let ordered = $derived(row ? [...row.signals].sort((a, b) => b.weight - a.weight) : []);
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col p-0 sm:max-w-lg">
		{#if row}
			<Sheet.Header class="gap-2 border-b px-5 py-4">
				<Sheet.Title class="flex items-center gap-2 font-mono text-sm wrap-anywhere">
					{row.host}
					<CopyButton value={row.host} class="size-5" />
				</Sheet.Title>
				<div class="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
					<span class="font-medium {BAND_TEXT[row.band] ?? ''}"
						>{interestCatalog.bandLabel(row.band)}</span
					>
					{#if row.http_status != null}
						<span class="tabular-nums">{row.http_status}</span>
					{/if}
					{#if row.tech.length}
						<span class="flex items-center gap-1">
							<TechIcon name={row.tech[0]} class="size-3" />
							{row.tech.join(', ')}
						</span>
					{/if}
					{#if row.asn_org}<span>{row.asn_org}</span>{/if}
					{#if row.is_cdn}<Badge variant="info" class="text-[10px]">CDN</Badge>{/if}
					{#if row.is_new}<Badge variant="outline" class="text-[10px]">New</Badge>{/if}
				</div>
			</Sheet.Header>

			<ScrollArea.Root class="min-h-0 flex-1">
				<div class="flex flex-col gap-5 px-5 py-4">
					<section class="flex flex-col gap-3">
						<h3 class="text-[11px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">
							Signals
						</h3>
						{#each ordered as signal (signal.source + signal.kind)}
							{@const Icon = kindIcon(signal.kind)}
							{@const isAi = signal.source === INTEREST_SOURCE.AI}
							<div
								class="flex flex-col gap-1.5 border-l-2 pl-3 {isAi
									? 'border-info/50'
									: signal.source === INTEREST_SOURCE.CORRELATION
										? 'border-border'
										: 'border-primary/50'}"
							>
								<span class="flex flex-wrap items-center gap-2 text-[12.5px] font-medium">
									<Icon class="size-3.5 text-muted-foreground" />
									{signal.kind_label}
									<span
										class="rounded border px-1 py-px text-[10px] font-normal {sourceChipClass(
											signal.source
										)}"
									>
										{isAi
											? 'AI judgement'
											: signal.label || interestCatalog.sourceLabel(signal.source)}
									</span>
								</span>
								{#if signal.reason}
									<p class="text-[12.5px] text-foreground/80">{signal.reason}</p>
								{:else}
									<p class="text-[12.5px] text-muted-foreground">
										{interestCatalog.kind(signal.kind)?.help ?? ''}
									</p>
								{/if}
								{#if isAi}
									<p class="flex items-center gap-1.5 text-[11px] text-muted-foreground">
										<Sparkle class="size-3 text-info" />
										Written by {signal.model ?? 'a model'}. A judgement, not an observation.
									</p>
								{:else if signal.evidence}
									<p
										class="rounded border border-border bg-accent/40 p-2 font-mono text-[11px] break-all text-muted-foreground"
									>
										{signal.evidence}
									</p>
								{/if}
							</div>
						{/each}
					</section>

					{#if row.page_title || row.resolved_ips.length}
						<section class="flex flex-col gap-2">
							<h3
								class="text-[11px] font-semibold tracking-[0.08em] text-muted-foreground uppercase"
							>
								Observed
							</h3>
							{#if row.page_title}
								<p class="text-[12.5px]">{row.page_title}</p>
							{/if}
							{#if row.resolved_ips.length}
								<p class="font-mono text-[11px] text-muted-foreground">
									{row.resolved_ips.join(', ')}
								</p>
							{/if}
						</section>
					{/if}
				</div>
			</ScrollArea.Root>

			<Sheet.Footer class="flex-row flex-wrap gap-2 border-t px-5 py-3">
				<Button size="sm" onclick={() => onOpenAssets(row)}>
					Open in Web Assets
					<ArrowUpRight class="size-3.5" />
				</Button>
				<Button
					variant="outline"
					size="sm"
					onclick={() => {
						onDismiss(row);
						onOpenChange(false);
					}}
				>
					<X class="size-3.5" />
					Not interesting
				</Button>
			</Sheet.Footer>
		{/if}
	</Sheet.Content>
</Sheet.Root>
