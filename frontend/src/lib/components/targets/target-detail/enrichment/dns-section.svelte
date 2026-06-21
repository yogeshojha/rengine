<script lang="ts">
	import type { DnsLookupRead, DnsRecordRead } from '$lib/types/target-detail';
	import CopyButton from '$lib/components/copy-button.svelte';
	import * as Table from '$lib/components/ui/table/index.js';
	import * as ScrollArea from '$lib/components/ui/scroll-area/index.js';
	import * as HoverCard from '$lib/components/ui/hover-card/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { CircleCheck, Globe } from 'lucide-svelte';

	interface Props {
		lookup: DnsLookupRead;
	}

	let { lookup }: Props = $props();

	const TYPE_ORDER = ['A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA', 'SRV', 'CAA', 'PTR'];

	let rows = $derived.by(() => {
		const o = (t: string) => {
			const i = TYPE_ORDER.indexOf(t);
			return i === -1 ? 99 : i;
		};
		return [...lookup.records].sort(
			(a, b) => o(a.record_type) - o(b.record_type) || (a.priority ?? 99) - (b.priority ?? 99)
		);
	});

	const TXT_PROVIDERS: Array<{ test: (v: string) => boolean; label: string }> = [
		{ test: (v) => v.startsWith('v=spf1'), label: 'SPF' },
		{ test: (v) => v.startsWith('v=DMARC'), label: 'DMARC' },
		{ test: (v) => v.startsWith('v=DKIM') || v.includes('DKIM'), label: 'DKIM' },
		{ test: (v) => v.startsWith('google-site-verification='), label: 'Google' },
		{ test: (v) => v.startsWith('MS='), label: 'MS365' },
		{ test: (v) => v.startsWith('apple-domain-verification='), label: 'Apple' },
		{ test: (v) => v.includes('facebook') || v.includes('fb'), label: 'Meta' },
		{ test: (v) => v.includes('docusign'), label: 'DocuSign' },
		{ test: (v) => v.includes('adobe'), label: 'Adobe' }
	];
	function detectProvider(val: string): string | null {
		return TXT_PROVIDERS.find((p) => p.test(val))?.label ?? null;
	}

	function hasMeta(rec: DnsRecordRead): boolean {
		return (
			(rec.record_type === 'SOA' && !!(rec.soa_email || rec.soa_serial)) || rec.record_type === 'SRV'
		);
	}
</script>

{#snippet table()}
	<Table.Root>
		<Table.Body>
			{#each rows as rec (rec.id)}
				<Table.Row class="group/rec border-border/15 hover:bg-muted/40">
					<Table.Cell class="py-1 w-12 align-top">
						<Badge
							variant="outline"
							class="font-mono text-[9px] px-1 py-0 text-muted-foreground border-border/60"
							>{rec.record_type}</Badge
						>
					</Table.Cell>
					<Table.Cell class="py-1 align-top max-w-0">
						<div class="flex items-start gap-1.5 min-w-0">
							{#if rec.record_type === 'MX' && rec.priority != null}
								<span class="shrink-0 mt-px text-[11px] font-mono tabular-nums text-muted-foreground/50"
									>{rec.priority}</span
								>
							{/if}
							{#if rec.record_type === 'TXT'}
								{@const p = detectProvider(rec.value)}
								{#if p}
									<Badge variant="secondary" class="shrink-0 mt-px text-[9px] px-1 py-0 font-medium"
										>{p}</Badge
									>
								{/if}
							{/if}
							{#if hasMeta(rec)}
								<HoverCard.Root>
									<HoverCard.Trigger class="min-w-0 flex-1 text-left">
										<code class="block truncate text-[11px] font-mono text-foreground/80"
											>{rec.value}</code
										>
									</HoverCard.Trigger>
									<HoverCard.Content class="w-auto space-y-0.5 text-[10px] font-mono">
										{#if rec.soa_email}<div>
												<span class="text-muted-foreground/60">email </span>{rec.soa_email}
											</div>{/if}
										{#if rec.soa_serial}<div>
												<span class="text-muted-foreground/60">serial </span>{rec.soa_serial}
											</div>{/if}
										{#if rec.record_type === 'SRV'}<div class="text-muted-foreground/60">
												pri {rec.priority} · wt {rec.weight} · :{rec.port}
											</div>{/if}
									</HoverCard.Content>
								</HoverCard.Root>
							{:else}
								<code
									class="block min-w-0 flex-1 truncate text-[11px] font-mono text-foreground/80"
									title={rec.value}>{rec.value}</code
								>
							{/if}
							<div
								class="opacity-100 sm:opacity-0 sm:group-hover/rec:opacity-100 transition-opacity shrink-0"
							>
								<CopyButton value={rec.value} />
							</div>
						</div>
					</Table.Cell>
				</Table.Row>
			{/each}
		</Table.Body>
	</Table.Root>
{/snippet}

<div class="p-3 space-y-2.5">
	<div
		class="flex items-center gap-1.5 px-1 text-[10px] font-mono tabular-nums text-muted-foreground/60"
	>
		<CircleCheck class="h-3 w-3 text-muted-foreground/40" />
		<span>{lookup.status_code}</span>
		<span>·</span>
		<span>{lookup.records.length} records</span>
		{#if lookup.cdn}
			<span>·</span>
			<Globe class="h-3 w-3 text-muted-foreground/40" />
			<span>{lookup.cdn_name || 'CDN'}</span>
		{/if}
	</div>

	{#if rows.length > 8}
		<ScrollArea.Root class="h-[260px] rounded-md border border-border/15" scrollbarYClasses="w-1.5">
			{@render table()}
		</ScrollArea.Root>
	{:else if rows.length > 0}
		<div class="rounded-md border border-border/15">
			{@render table()}
		</div>
	{/if}
</div>
