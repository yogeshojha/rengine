<script lang="ts">
	import type { TargetBgpDetailResponse } from '$lib/types/target-detail';
	import { TargetType } from '$lib/types/target';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import CopyButton from '$lib/components/copy-button.svelte';
	import { Search, X, Copy, Check, ChevronRight, Mail, Info } from 'lucide-svelte';
	import { tick } from 'svelte';

	interface Props {
		bgp: TargetBgpDetailResponse;
		targetType: TargetType;
	}

	let { bgp, targetType }: Props = $props();

	// neighbour groups
	let upstream = $derived(bgp.neighbours.filter((n) => n.relationship === 'upstream'));
	let downstream = $derived(bgp.neighbours.filter((n) => n.relationship === 'downstream'));
	let uncertain = $derived(
		bgp.neighbours.filter((n) => n.relationship !== 'upstream' && n.relationship !== 'downstream')
	);

	let totalNeighbours = $derived(bgp.neighbours.length);

	// proportion percentages
	let upPct = $derived(
		totalNeighbours > 0 ? Math.round((upstream.length / totalNeighbours) * 100) : 0
	);
	let downPct = $derived(
		totalNeighbours > 0 ? Math.round((downstream.length / totalNeighbours) * 100) : 0
	);
	let latPct = $derived(totalNeighbours > 0 ? 100 - upPct - downPct : 0);

	// network position insight
	let positionLabel = $derived.by(() => {
		if (totalNeighbours === 0) return null;
		const downRatio = downstream.length / totalNeighbours;
		const upRatio = upstream.length / totalNeighbours;
		if (downRatio > 0.6)
			return {
				label: 'Transit provider',
				desc: 'high downstream ratio indicates significant customer base',
				color: 'emerald' as const
			};
		if (upRatio > 0.6)
			return {
				label: 'Leaf network',
				desc: 'primarily consumes transit, limited downstream presence',
				color: 'blue' as const
			};
		return {
			label: 'Mid-tier network',
			desc: 'balanced upstream/downstream indicating regional connectivity',
			color: 'amber' as const
		};
	});

	const INSIGHT_COLORS = {
		emerald: 'bg-emerald-500/8 border-emerald-500/20 text-emerald-400',
		blue: 'bg-blue-500/8 border-blue-500/20 text-blue-400',
		amber: 'bg-amber-500/8 border-amber-500/20 text-amber-400'
	};

	// search
	let query = $state('');
	let topologyEl = $state<HTMLDivElement | null>(null);

	let matchCounts = $derived.by(() => {
		const q = query.trim().toUpperCase();
		if (!q) return null;
		let up = 0,
			down = 0,
			lat = 0;
		upstream.forEach((n) => {
			if (String(n.neighbour_asn).includes(q) || `AS${n.neighbour_asn}`.toUpperCase().includes(q))
				up++;
		});
		downstream.forEach((n) => {
			if (String(n.neighbour_asn).includes(q) || `AS${n.neighbour_asn}`.toUpperCase().includes(q))
				down++;
		});
		uncertain.forEach((n) => {
			if (String(n.neighbour_asn).includes(q) || `AS${n.neighbour_asn}`.toUpperCase().includes(q))
				lat++;
		});
		return { total: up + down + lat, up, down, lat };
	});

	function isMatch(asn: number): boolean {
		const q = query.trim().toUpperCase();
		if (!q) return false;
		return String(asn).includes(q) || `AS${asn}`.toUpperCase().includes(q);
	}

	function hasQuery(): boolean {
		return query.trim().length > 0;
	}

	// auto-scroll to first match
	$effect(() => {
		if (query.trim()) {
			tick().then(() => {
				if (!topologyEl) return;
				const first = topologyEl.querySelector('[data-match="true"]');
				if (first) {
					first.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
				}
			});
		}
	});

	// copy groups
	let copiedGroup = $state<string | null>(null);
	function copyAll(group: 'up' | 'down' | 'lat') {
		const list = group === 'up' ? upstream : group === 'down' ? downstream : uncertain;
		const text = list.map((n) => `AS${n.neighbour_asn}`).join('\n');
		navigator.clipboard.writeText(text);
		copiedGroup = group;
		setTimeout(() => (copiedGroup = null), 1500);
	}

	// copy prefixes
	let copiedPrefixes = $state(false);
	function copyPrefixes() {
		const text = bgp.announced_prefixes.map((p) => p.prefix).join('\n');
		navigator.clipboard.writeText(text);
		copiedPrefixes = true;
		setTimeout(() => (copiedPrefixes = false), 1500);
	}

	// collapsible sections
	let showNetwork = $state(false);
	let showPrefixes = $state(false);
	let showPrefixOverview = $state(false);
	let showRelated = $state(false);
	let showAbuse = $state(false);

	function fmtDate(d: string | null): string {
		if (!d) return '—';
		try {
			return new Date(d).toLocaleDateString('en-US', {
				year: 'numeric',
				month: 'short',
				day: 'numeric'
			});
		} catch {
			return d;
		}
	}
</script>

{#snippet copyAllBtn(group: 'up' | 'down' | 'lat')}
	<button
		class="flex items-center gap-1 text-[8px] text-muted-foreground/40 border border-border/40 rounded px-1.5 py-0.5
			hover:text-foreground/60 hover:border-border/60 hover:bg-accent/5 transition-all"
		onclick={() => copyAll(group)}
	>
		{#if copiedGroup === group}
			<Check class="h-2.5 w-2.5 text-emerald-400" />
			<span class="text-emerald-400">copied</span>
		{:else}
			<Copy class="h-2.5 w-2.5" />
			<span>copy all</span>
		{/if}
	</button>
{/snippet}

{#snippet chipGroup(items: typeof upstream, cls: string, hlCls: string)}
	<ScrollArea class="h-[88px]">
		<div class="flex flex-wrap gap-1 pr-1">
			{#each items as n (n.neighbour_asn)}
				{@const matched = isMatch(n.neighbour_asn)}
				{@const dimmed = hasQuery() && !matched}
				<span
					data-match={matched ? 'true' : undefined}
					class="text-[9px] font-mono font-medium tabular-nums rounded border px-1.5 py-0.5 transition-all duration-150
						{cls}
						{dimmed ? 'opacity-[0.15]' : ''}
						{matched ? hlCls : ''}
						{!hasQuery() ? 'hover:-translate-y-px' : ''}">AS{n.neighbour_asn}</span
				>
			{/each}
		</div>
	</ScrollArea>
{/snippet}

<div class="bgp-topology" bind:this={topologyEl}>
	<!-- proportion bar -->
	{#if totalNeighbours > 0}
		<div class="px-3 pt-3 pb-2 space-y-1.5">
			<div class="h-1 rounded-full bg-border/40 flex gap-px overflow-hidden">
				{#if upstream.length > 0}
					<div
						class="h-full rounded-full bg-blue-400 transition-all duration-500"
						style="width: {upPct}%"
					></div>
				{/if}
				{#if downstream.length > 0}
					<div
						class="h-full rounded-full bg-emerald-400 transition-all duration-500"
						style="width: {downPct}%"
					></div>
				{/if}
				{#if uncertain.length > 0}
					<div
						class="h-full rounded-full bg-amber-400/60 transition-all duration-500"
						style="width: {latPct}%"
					></div>
				{/if}
			</div>
			<div class="flex justify-between text-[9px] font-mono text-muted-foreground/50">
				<span class="flex items-center gap-1">
					<span class="h-[5px] w-[5px] rounded-full bg-blue-400"></span>
					<span class="font-semibold text-foreground/60">{upstream.length}</span> up
				</span>
				<span class="flex items-center gap-1">
					<span class="h-[5px] w-[5px] rounded-full bg-emerald-400"></span>
					<span class="font-semibold text-foreground/60">{downstream.length}</span> down
				</span>
				<span class="flex items-center gap-1">
					<span class="h-[5px] w-[5px] rounded-full bg-amber-400/60"></span>
					<span class="font-semibold text-foreground/60">{uncertain.length}</span> lateral
				</span>
			</div>
		</div>
	{/if}

	<!-- search -->
	{#if totalNeighbours > 10}
		<div class="px-3 pb-2">
			<div class="relative flex items-center">
				<Search class="absolute left-2 h-3 w-3 text-muted-foreground/40 pointer-events-none" />
				<input
					type="text"
					bind:value={query}
					class="w-full bg-accent/5 border border-border/40 rounded-md py-1 pl-7 pr-7 text-[10px] font-mono
						text-foreground placeholder:text-muted-foreground/30 outline-none
						focus:border-border/60 transition-colors"
					placeholder="Find ASN…"
					autocomplete="off"
					spellcheck="false"
				/>
				{#if query}
					<button
						class="absolute right-1.5 text-muted-foreground/40 hover:text-foreground/60 transition-colors"
						onclick={() => (query = '')}
					>
						<X class="h-3 w-3" />
					</button>
				{/if}
			</div>
			{#if matchCounts}
				<p class="text-[9px] font-mono text-muted-foreground/40 mt-1">
					<span class="font-semibold text-foreground/60">{matchCounts.total}</span> found
					{#if matchCounts.up > 0}<span> · {matchCounts.up} upstream</span>{/if}
					{#if matchCounts.down > 0}<span> · {matchCounts.down} downstream</span>{/if}
					{#if matchCounts.lat > 0}<span> · {matchCounts.lat} uncertain</span>{/if}
				</p>
			{/if}
		</div>
	{/if}

	<!-- topology flow -->
	<div class="px-3 pb-3 space-y-1">
		<!-- UPSTREAM -->
		{#if upstream.length > 0}
			<div>
				<div class="flex items-center justify-between mb-1.5">
					<div
						class="flex items-center gap-1.5 text-[8px] font-semibold uppercase tracking-[0.1em] text-blue-400"
					>
						<span>Upstream · {upstream.length}</span>
						<span class="flex-1 h-px bg-border/30 min-w-3"></span>
					</div>
					{@render copyAllBtn('up')}
				</div>
				{@render chipGroup(
					upstream,
					'bg-blue-500/8 text-blue-400 border-blue-500/15 hover:bg-blue-500/15 hover:border-blue-500/25',
					'bg-blue-500/20 border-blue-500/40 shadow-[0_0_8px_rgba(96,165,250,0.2)]'
				)}
			</div>
		{/if}

		<!-- flow lines in -->
		{#if upstream.length > 0}
			<div class="flex justify-center py-0.5">
				<svg width="140" height="18" viewBox="0 0 140 18" class="block">
					<line
						x1="20"
						y1="0"
						x2="70"
						y2="16"
						class="flow-in"
						stroke="rgba(96,165,250,0.2)"
						stroke-width="1"
					/>
					<line
						x1="50"
						y1="0"
						x2="70"
						y2="16"
						class="flow-in"
						stroke="rgba(96,165,250,0.3)"
						stroke-width="1"
					/>
					<line
						x1="70"
						y1="0"
						x2="70"
						y2="16"
						class="flow-in"
						stroke="rgba(96,165,250,0.35)"
						stroke-width="1"
					/>
					<line
						x1="90"
						y1="0"
						x2="70"
						y2="16"
						class="flow-in"
						stroke="rgba(96,165,250,0.3)"
						stroke-width="1"
					/>
					<line
						x1="120"
						y1="0"
						x2="70"
						y2="16"
						class="flow-in"
						stroke="rgba(96,165,250,0.2)"
						stroke-width="1"
					/>
				</svg>
			</div>
		{/if}

		<!-- TARGET NODE -->
		{#if bgp.as_overview}
			<div class="flex justify-center py-2">
				<div
					class="relative flex items-center gap-2.5 px-4 py-2 rounded-lg
					bg-gradient-to-br from-white/[0.04] to-white/[0.01]
					border border-white/[0.08]"
				>
					<div
						class="absolute -inset-[5px] rounded-xl border border-white/[0.03] pointer-events-none"
					></div>
					<div class="relative h-2 w-2 rounded-full bg-foreground shrink-0">
						<div
							class="absolute -inset-[3px] rounded-full border border-white/10 target-pulse"
						></div>
					</div>
					<div>
						<p class="text-[13px] font-semibold font-mono tracking-tight">
							AS{bgp.as_overview.asn}
						</p>
						<p class="text-[9px] text-muted-foreground/50">{bgp.as_overview.holder || '—'}</p>
					</div>
				</div>
			</div>
		{/if}

		<!-- flow lines out -->
		{#if downstream.length > 0}
			<div class="flex justify-center py-0.5">
				<svg width="140" height="18" viewBox="0 0 140 18" class="block">
					<line
						x1="70"
						y1="2"
						x2="10"
						y2="18"
						class="flow-out"
						stroke="rgba(52,211,153,0.15)"
						stroke-width="1"
					/>
					<line
						x1="70"
						y1="2"
						x2="40"
						y2="18"
						class="flow-out"
						stroke="rgba(52,211,153,0.2)"
						stroke-width="1"
					/>
					<line
						x1="70"
						y1="2"
						x2="70"
						y2="18"
						class="flow-out"
						stroke="rgba(52,211,153,0.3)"
						stroke-width="1"
					/>
					<line
						x1="70"
						y1="2"
						x2="100"
						y2="18"
						class="flow-out"
						stroke="rgba(52,211,153,0.2)"
						stroke-width="1"
					/>
					<line
						x1="70"
						y1="2"
						x2="130"
						y2="18"
						class="flow-out"
						stroke="rgba(52,211,153,0.15)"
						stroke-width="1"
					/>
				</svg>
			</div>
		{/if}

		<!-- DOWNSTREAM -->
		{#if downstream.length > 0}
			<div>
				<div class="flex items-center justify-between mb-1.5">
					<div
						class="flex items-center gap-1.5 text-[8px] font-semibold uppercase tracking-[0.1em] text-emerald-400"
					>
						<span>Downstream · {downstream.length}</span>
						<span class="flex-1 h-px bg-border/30 min-w-3"></span>
					</div>
					{@render copyAllBtn('down')}
				</div>
				{@render chipGroup(
					downstream,
					'bg-emerald-500/8 text-emerald-400 border-emerald-500/15 hover:bg-emerald-500/15 hover:border-emerald-500/25',
					'bg-emerald-500/20 border-emerald-500/40 shadow-[0_0_8px_rgba(52,211,153,0.2)]'
				)}
			</div>
		{/if}

		<!-- UNCERTAIN -->
		{#if uncertain.length > 0}
			<div class="mt-2">
				<div class="flex items-center justify-between mb-1.5">
					<div
						class="flex items-center gap-1.5 text-[8px] font-semibold uppercase tracking-[0.1em] text-amber-400"
					>
						<span>Uncertain · {uncertain.length}</span>
						<span class="flex-1 h-px bg-border/30 min-w-3"></span>
					</div>
					{@render copyAllBtn('lat')}
				</div>
				{@render chipGroup(
					uncertain,
					'bg-amber-500/8 text-amber-400 border-amber-500/12 hover:bg-amber-500/12 hover:border-amber-500/20',
					'bg-amber-500/15 border-amber-500/35 shadow-[0_0_8px_rgba(251,191,36,0.2)]'
				)}
			</div>
		{/if}

		<!-- position insight — colored -->
		{#if positionLabel}
			<div
				class="mt-3 flex items-start gap-2 px-2.5 py-2 rounded-md border {INSIGHT_COLORS[
					positionLabel.color
				]}"
			>
				<Info class="h-3.5 w-3.5 shrink-0 mt-px opacity-70" />
				<p class="text-[10px] leading-relaxed">
					<span class="font-semibold">{positionLabel.label}</span>
					<span class="opacity-60"> — {positionLabel.desc}</span>
				</p>
			</div>
		{/if}
	</div>

	<!-- DETAIL SECTIONS (collapsible) -->
	<div class="border-t border-border/10 px-3 py-2 space-y-1">
		<!-- network info -->
		{#if bgp.network_info.length > 0}
			<div>
				<button
					class="flex items-center gap-1.5 w-full text-[10px] text-muted-foreground/40 hover:text-foreground/60 transition-colors py-1"
					onclick={() => (showNetwork = !showNetwork)}
				>
					<ChevronRight
						class="h-2.5 w-2.5 transition-transform duration-150 {showNetwork ? 'rotate-90' : ''}"
					/>
					<span>Network Info ({bgp.network_info.length})</span>
				</button>
				{#if showNetwork}
					<div class="mt-1 rounded-md border border-border/20 overflow-hidden">
						{#each bgp.network_info as ni, i (ni.ip)}
							<div
								class="flex items-center gap-2 px-2.5 py-1.5 text-[10px] group/ni
								{i > 0 ? 'border-t border-border/10' : ''} hover:bg-accent/5 transition-colors"
							>
								<code class="font-mono text-foreground/70">{ni.ip}</code>
								<span class="text-muted-foreground/25">→</span>
								<code class="font-mono text-foreground/55 flex-1">{ni.prefix || '—'}</code>
								<span class="font-mono text-muted-foreground/35 text-[9px]">AS{ni.asn || '—'}</span>
								<div class="opacity-0 group-hover/ni:opacity-100 transition-opacity">
									<CopyButton value={ni.prefix || ni.ip} />
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- announced prefixes -->
		{#if bgp.announced_prefixes.length > 0}
			<div>
				<button
					class="flex items-center gap-1.5 w-full text-[10px] text-muted-foreground/40 hover:text-foreground/60 transition-colors py-1"
					onclick={() => (showPrefixes = !showPrefixes)}
				>
					<ChevronRight
						class="h-2.5 w-2.5 transition-transform duration-150 {showPrefixes ? 'rotate-90' : ''}"
					/>
					<span>Announced Prefixes ({bgp.announced_prefixes.length})</span>
				</button>
				{#if showPrefixes}
					<div class="mt-1">
						<div class="flex justify-end mb-1">
							<button
								class="flex items-center gap-1 text-[8px] text-muted-foreground/40 border border-border/40 rounded px-1.5 py-0.5
									hover:text-foreground/60 hover:border-border/60 hover:bg-accent/5 transition-all"
								onclick={copyPrefixes}
							>
								{#if copiedPrefixes}
									<Check class="h-2.5 w-2.5 text-emerald-400" />
									<span class="text-emerald-400">copied</span>
								{:else}
									<Copy class="h-2.5 w-2.5" />
									<span>copy all</span>
								{/if}
							</button>
						</div>
						<ScrollArea class="h-[160px] rounded-md border border-border/20">
							<div>
								{#each bgp.announced_prefixes as pfx, i (pfx.prefix)}
									<div
										class="flex items-center gap-2 px-2.5 py-1.5 text-[10px]
										{i > 0 ? 'border-t border-border/10' : ''} hover:bg-accent/5 transition-colors"
									>
										<code class="font-mono text-foreground/70 flex-1">{pfx.prefix}</code>
										<span class="text-[9px] text-muted-foreground/25">v{pfx.ip_version}</span>
										<span class="font-mono tabular-nums text-[9px] text-muted-foreground/25"
											>{fmtDate(pfx.first_seen)}</span
										>
									</div>
								{/each}
							</div>
						</ScrollArea>
					</div>
				{/if}
			</div>
		{/if}

		<!-- prefix overview -->
		{#if bgp.prefix_overview.length > 0}
			<div>
				<button
					class="flex items-center gap-1.5 w-full text-[10px] text-muted-foreground/40 hover:text-foreground/60 transition-colors py-1"
					onclick={() => (showPrefixOverview = !showPrefixOverview)}
				>
					<ChevronRight
						class="h-2.5 w-2.5 transition-transform duration-150 {showPrefixOverview
							? 'rotate-90'
							: ''}"
					/>
					<span>Prefix Overview ({bgp.prefix_overview.length})</span>
				</button>
				{#if showPrefixOverview}
					<div class="mt-1 rounded-md border border-border/20 overflow-hidden">
						{#each bgp.prefix_overview as po, i}
							<div
								class="flex items-center gap-2 px-2.5 py-1.5 text-[10px]
								{i > 0 ? 'border-t border-border/10' : ''} hover:bg-accent/5 transition-colors"
							>
								<code class="font-mono text-foreground/70 flex-1">{po.prefix}</code>
								<span class="text-muted-foreground/35 text-[9px]">AS{po.asn}</span>
								<span
									class="h-1.5 w-1.5 rounded-full {po.is_announced
										? 'bg-emerald-500'
										: 'bg-red-500'}"
								></span>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- related prefixes -->
		{#if bgp.related_prefixes.length > 0}
			<div>
				<button
					class="flex items-center gap-1.5 w-full text-[10px] text-muted-foreground/40 hover:text-foreground/60 transition-colors py-1"
					onclick={() => (showRelated = !showRelated)}
				>
					<ChevronRight
						class="h-2.5 w-2.5 transition-transform duration-150 {showRelated ? 'rotate-90' : ''}"
					/>
					<span>Related Prefixes ({bgp.related_prefixes.length})</span>
				</button>
				{#if showRelated}
					<div class="mt-1 rounded-md border border-border/20 overflow-hidden">
						{#each bgp.related_prefixes as rp, i}
							<div
								class="flex items-center gap-2 px-2.5 py-1.5 text-[10px]
								{i > 0 ? 'border-t border-border/10' : ''} hover:bg-accent/5 transition-colors"
							>
								<code class="font-mono text-foreground/70 flex-1">{rp.related_prefix}</code>
								<Badge variant="outline" class="text-[7px] h-3.5 px-1">{rp.relationship}</Badge>
								{#if rp.origin_asn}<span class="font-mono text-muted-foreground/35 text-[9px]"
										>AS{rp.origin_asn}</span
									>{/if}
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- abuse contacts -->
		{#if bgp.abuse_contacts.length > 0}
			<div>
				<button
					class="flex items-center gap-1.5 w-full text-[10px] text-muted-foreground/40 hover:text-foreground/60 transition-colors py-1"
					onclick={() => (showAbuse = !showAbuse)}
				>
					<ChevronRight
						class="h-2.5 w-2.5 transition-transform duration-150 {showAbuse ? 'rotate-90' : ''}"
					/>
					<span>Abuse Contacts ({bgp.abuse_contacts.length})</span>
				</button>
				{#if showAbuse}
					<div class="mt-1 space-y-1">
						{#each bgp.abuse_contacts as ac}
							<div class="flex items-center gap-1.5 text-[10px] group/ac">
								<Mail class="h-3 w-3 text-muted-foreground/25" />
								<span class="font-mono text-foreground/60">{ac.abuse_email}</span>
								{#if ac.rir}<Badge variant="outline" class="text-[7px] h-3.5 px-1">{ac.rir}</Badge
									>{/if}
								<div class="opacity-0 group-hover/ac:opacity-100 transition-opacity ml-auto">
									<CopyButton value={ac.abuse_email} />
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	/* animated flow lines */
	.flow-in,
	.flow-out {
		stroke-dasharray: 4, 3;
		animation: dash-flow 1.5s linear infinite;
	}
	.flow-in {
		animation-direction: reverse;
	}

	@keyframes dash-flow {
		to {
			stroke-dashoffset: -7;
		}
	}

	/* target pulse */
	.target-pulse {
		animation: pulse-ring 2.5s ease-out infinite;
	}
	@keyframes pulse-ring {
		0% {
			transform: scale(1);
			opacity: 0.4;
		}
		100% {
			transform: scale(2.5);
			opacity: 0;
		}
	}
</style>
