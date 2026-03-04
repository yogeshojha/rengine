<script lang="ts">
	import type { DnsLookupRead, DnsRecordRead } from '$lib/types/target-detail';
	import CopyButton from '$lib/components/copy-button.svelte';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { CircleCheck, Globe } from 'lucide-svelte';

	interface Props {
		lookup: DnsLookupRead;
	}

	let { lookup }: Props = $props();

	const TYPE_ORDER = ['A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA', 'SRV', 'CAA', 'PTR'];
	const TYPE_COLOR: Record<string, { active: string; inactive: string }> = {
		A: {
			active: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
			inactive: 'text-blue-400/40 border-transparent hover:border-blue-500/15 hover:bg-blue-500/5'
		},
		AAAA: {
			active: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30',
			inactive:
				'text-indigo-400/40 border-transparent hover:border-indigo-500/15 hover:bg-indigo-500/5'
		},
		CNAME: {
			active: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
			inactive: 'text-cyan-400/40 border-transparent hover:border-cyan-500/15 hover:bg-cyan-500/5'
		},
		MX: {
			active: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
			inactive:
				'text-amber-400/40 border-transparent hover:border-amber-500/15 hover:bg-amber-500/5'
		},
		NS: {
			active: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
			inactive:
				'text-emerald-400/40 border-transparent hover:border-emerald-500/15 hover:bg-emerald-500/5'
		},
		TXT: {
			active: 'bg-violet-500/15 text-violet-400 border-violet-500/30',
			inactive:
				'text-violet-400/40 border-transparent hover:border-violet-500/15 hover:bg-violet-500/5'
		},
		SOA: {
			active: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
			inactive: 'text-rose-400/40 border-transparent hover:border-rose-500/15 hover:bg-rose-500/5'
		},
		SRV: {
			active: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
			inactive:
				'text-orange-400/40 border-transparent hover:border-orange-500/15 hover:bg-orange-500/5'
		},
		CAA: {
			active: 'bg-teal-500/15 text-teal-400 border-teal-500/30',
			inactive: 'text-teal-400/40 border-transparent hover:border-teal-500/15 hover:bg-teal-500/5'
		},
		PTR: {
			active: 'bg-pink-500/15 text-pink-400 border-pink-500/30',
			inactive: 'text-pink-400/40 border-transparent hover:border-pink-500/15 hover:bg-pink-500/5'
		}
	};

	const FALLBACK = {
		active: 'bg-muted text-foreground border-border',
		inactive: 'text-muted-foreground border-transparent hover:bg-muted/50'
	};

	let grouped = $derived.by(() => {
		const map = new Map<string, DnsRecordRead[]>();
		for (const rec of lookup.records) {
			const list = map.get(rec.record_type) ?? [];
			list.push(rec);
			map.set(rec.record_type, list);
		}
		return TYPE_ORDER.filter((t) => map.has(t)).map((t) => ({ type: t, records: map.get(t)! }));
	});

	let activeType = $state('');
	$effect(() => {
		if (grouped.length > 0 && !grouped.some((g) => g.type === activeType)) {
			activeType = grouped[0].type;
		}
	});

	let activeRecords = $derived(grouped.find((g) => g.type === activeType)?.records ?? []);

	// MX: sort by priority
	let sortedRecords = $derived(
		activeType === 'MX'
			? [...activeRecords].sort((a, b) => (a.priority ?? 99) - (b.priority ?? 99))
			: activeRecords
	);

	// TXT provider detection
	const TXT_PROVIDERS: Array<{ test: (v: string) => boolean; label: string; color: string }> = [
		{
			test: (v) => v.startsWith('v=spf1'),
			label: 'SPF',
			color: 'text-emerald-400 bg-emerald-500/10'
		},
		{ test: (v) => v.startsWith('v=DMARC'), label: 'DMARC', color: 'text-blue-400 bg-blue-500/10' },
		{
			test: (v) => v.startsWith('v=DKIM') || v.includes('DKIM'),
			label: 'DKIM',
			color: 'text-cyan-400 bg-cyan-500/10'
		},
		{
			test: (v) => v.startsWith('google-site-verification='),
			label: 'Google',
			color: 'text-red-400 bg-red-500/10'
		},
		{ test: (v) => v.startsWith('MS='), label: 'MS365', color: 'text-orange-400 bg-orange-500/10' },
		{
			test: (v) => v.startsWith('apple-domain-verification='),
			label: 'Apple',
			color: 'text-zinc-400 bg-zinc-500/10'
		},
		{
			test: (v) => v.includes('facebook') || v.includes('fb'),
			label: 'Meta',
			color: 'text-blue-400 bg-blue-500/10'
		},
		{
			test: (v) => v.includes('docusign'),
			label: 'DocuSign',
			color: 'text-yellow-400 bg-yellow-500/10'
		},
		{ test: (v) => v.includes('adobe'), label: 'Adobe', color: 'text-red-400 bg-red-500/10' }
	];

	function detectProvider(val: string): { label: string; color: string } | null {
		return TXT_PROVIDERS.find((p) => p.test(val)) ?? null;
	}
</script>

<div class="p-3 space-y-2.5">
	<!-- status line -->
	<div class="flex items-center gap-1.5 text-[10px] text-muted-foreground/50">
		<CircleCheck class="h-3 w-3 text-emerald-500/50" />
		<span class="font-mono">{lookup.status_code}</span>
		<span>·</span>
		<span class="tabular-nums">{lookup.records.length} records</span>
		{#if lookup.cdn}
			<span>·</span>
			<Globe class="h-3 w-3 text-muted-foreground/40" />
			<span>{lookup.cdn_name || 'CDN'}</span>
		{/if}
	</div>

	<!-- type tabs -->
	<div class="flex flex-wrap gap-1">
		{#each grouped as g (g.type)}
			{@const c = TYPE_COLOR[g.type] ?? FALLBACK}
			{@const isActive = activeType === g.type}
			<button
				class="text-[9px] font-mono font-semibold tabular-nums rounded border px-1.5 py-0.5 transition-all duration-150
					{isActive ? c.active : c.inactive}"
				onclick={() => (activeType = g.type)}
			>
				{g.type}<span class="opacity-40 ml-0.5">{g.records.length}</span>
			</button>
		{/each}
	</div>

	<!-- unified table — scrollable -->
	{#if sortedRecords.length > 0}
		<ScrollArea class="h-[320px] rounded-md border border-border/20">
			{#each sortedRecords as rec, i (rec.id)}
				<div
					class="px-2.5 py-1.5 group/rec
					{i > 0 ? 'border-t border-border/10' : ''}
					hover:bg-accent/5 transition-colors"
				>
					<!-- row content varies slightly by type, but same container -->
					<div class="flex items-start gap-2">
						<!-- MX: priority prefix -->
						{#if activeType === 'MX' && rec.priority != null}
							<span
								class="text-[10px] font-mono tabular-nums text-amber-400/40 w-5 text-right shrink-0 pt-px"
							>
								{rec.priority}
							</span>
						{/if}

						<!-- CAA: tag prefix -->
						{#if activeType === 'CAA' && rec.caa_tag}
							<span
								class="text-[9px] font-mono font-semibold rounded bg-teal-500/10 text-teal-400/60 px-1 shrink-0 mt-px"
							>
								{rec.caa_tag}
							</span>
						{/if}

						<!-- SRV: port suffix area handled below -->

						<!-- value -->
						<div class="min-w-0 flex-1">
							{#if activeType === 'TXT'}
								{@const provider = detectProvider(rec.value)}
								{#if provider}
									<span
										class="inline-block text-[8px] font-semibold uppercase tracking-wider rounded px-1 py-px mb-1 {provider.color}"
									>
										{provider.label}
									</span>
								{/if}
							{/if}

							<code
								class="block text-[10px] font-mono leading-relaxed text-foreground/65 break-all"
							>
								{rec.value}
							</code>

							<!-- SOA: metadata below value -->
							{#if activeType === 'SOA' && (rec.soa_email || rec.soa_serial)}
								<div class="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 pt-1 border-t border-border/10">
									{#if rec.soa_email}
										<div class="flex items-center gap-1 text-[9px]">
											<span class="text-muted-foreground/30">email</span>
											<span class="font-mono text-foreground/45">{rec.soa_email}</span>
										</div>
									{/if}
									{#if rec.soa_serial}
										<div class="flex items-center gap-1 text-[9px]">
											<span class="text-muted-foreground/30">serial</span>
											<span class="font-mono text-foreground/45">{rec.soa_serial}</span>
										</div>
									{/if}
								</div>
							{/if}

							<!-- SRV: metadata below value -->
							{#if activeType === 'SRV'}
								<div
									class="flex items-center gap-2 mt-0.5 text-[9px] font-mono text-muted-foreground/25"
								>
									{#if rec.priority != null}<span>pri {rec.priority}</span>{/if}
									{#if rec.weight != null}<span>wt {rec.weight}</span>{/if}
									{#if rec.port != null}<span class="text-orange-400/40">:{rec.port}</span>{/if}
								</div>
							{/if}
						</div>

						<!-- copy -->
						<div class="opacity-0 group-hover/rec:opacity-100 transition-opacity shrink-0 pt-px">
							<CopyButton value={rec.value} />
						</div>
					</div>
				</div>
			{/each}
		</ScrollArea>
	{/if}
</div>
