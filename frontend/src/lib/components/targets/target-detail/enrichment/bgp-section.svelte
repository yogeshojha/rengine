<script lang="ts">
	import type { TargetBgpDetailResponse } from '$lib/types/target-detail';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import * as ScrollArea from '$lib/components/ui/scroll-area/index.js';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import Copy from '@lucide/svelte/icons/copy';
	import Check from '@lucide/svelte/icons/check';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Mail from '@lucide/svelte/icons/mail';
	import Info from '@lucide/svelte/icons/info';
	import { tick } from 'svelte';
	import { formatShortDate } from '$lib/utilities/dates';

	interface Props {
		bgp: TargetBgpDetailResponse;
	}

	let { bgp }: Props = $props();

	const byPower = (a: { power: number }, b: { power: number }) => (b.power ?? 0) - (a.power ?? 0);
	let upstream = $derived(
		bgp.neighbours.filter((n) => n.relationship === 'upstream').sort(byPower)
	);
	let downstream = $derived(
		bgp.neighbours.filter((n) => n.relationship === 'downstream').sort(byPower)
	);
	let uncertain = $derived(
		bgp.neighbours
			.filter((n) => n.relationship !== 'upstream' && n.relationship !== 'downstream')
			.sort(byPower)
	);

	let totalNeighbours = $derived(bgp.neighbours.length);

	let upPct = $derived(
		totalNeighbours > 0 ? Math.round((upstream.length / totalNeighbours) * 100) : 0
	);
	let downPct = $derived(
		totalNeighbours > 0 ? Math.round((downstream.length / totalNeighbours) * 100) : 0
	);
	let latPct = $derived(totalNeighbours > 0 ? 100 - upPct - downPct : 0);

	let positionLabel = $derived.by(() => {
		if (totalNeighbours === 0) return null;
		const downRatio = downstream.length / totalNeighbours;
		const upRatio = upstream.length / totalNeighbours;
		if (downRatio > 0.6)
			return {
				label: 'Transit provider',
				desc: 'high downstream ratio indicates significant customer base'
			};
		if (upRatio > 0.6)
			return {
				label: 'Leaf network',
				desc: 'primarily consumes transit, limited downstream presence'
			};
		return {
			label: 'Mid-tier network',
			desc: 'balanced upstream/downstream indicating regional connectivity'
		};
	});

	const INSIGHT_PANEL = 'bg-muted/40 border-border/50 text-foreground/70';

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

	async function writeClipboard(text: string): Promise<boolean> {
		if (navigator.clipboard && window.isSecureContext) {
			try {
				await navigator.clipboard.writeText(text);
				return true;
			} catch {
				// fall through
			}
		}
		try {
			const ta = document.createElement('textarea');
			ta.value = text;
			ta.style.position = 'fixed';
			ta.style.opacity = '0';
			document.body.appendChild(ta);
			ta.focus();
			ta.select();
			const ok = document.execCommand('copy');
			ta.remove();
			return ok;
		} catch {
			return false;
		}
	}

	let copiedGroup = $state<string | null>(null);
	async function copyAll(group: 'up' | 'down' | 'lat') {
		const list = group === 'up' ? upstream : group === 'down' ? downstream : uncertain;
		const text = list.map((n) => `AS${n.neighbour_asn}`).join('\n');
		if (!(await writeClipboard(text))) return;
		copiedGroup = group;
		setTimeout(() => (copiedGroup = null), 1500);
	}

	let copiedPrefixes = $state(false);
	async function copyPrefixes() {
		const text = bgp.announced_prefixes.map((p) => p.prefix).join('\n');
		if (!(await writeClipboard(text))) return;
		copiedPrefixes = true;
		setTimeout(() => (copiedPrefixes = false), 1500);
	}

	let showNetwork = $state(false);
	let showPrefixes = $state(false);
	let showPrefixOverview = $state(false);
	let showRelated = $state(false);
	let showAbuse = $state(false);

	function fmtDate(d: string | null): string {
		if (!d) return '—';
		try {
			return formatShortDate(d);
		} catch {
			return d;
		}
	}
</script>

{#snippet copyAllBtn(group: 'up' | 'down' | 'lat')}
	<Button
		variant="outline"
		size="sm"
		class="h-5 gap-1 px-1.5 text-[10px] text-muted-foreground/60"
		onclick={() => copyAll(group)}
	>
		{#if copiedGroup === group}
			<Check class="h-2.5 w-2.5" />
			<span>Copied</span>
		{:else}
			<Copy class="h-2.5 w-2.5" />
			<span>copy all</span>
		{/if}
	</Button>
{/snippet}

{#snippet chipList(items: typeof upstream)}
	<div class="flex flex-wrap gap-1 content-start p-1.5">
		{#each items as n (n.neighbour_asn)}
			{@const matched = isMatch(n.neighbour_asn)}
			{@const dimmed = hasQuery() && !matched}
			<span
				data-match={matched ? 'true' : undefined}
				class="text-[10px] font-mono font-medium tabular-nums rounded-md border px-1.5 py-0.5 transition-colors duration-150
					{matched
					? 'bg-chart-1/15 text-foreground border-chart-1/40'
					: 'bg-muted/60 text-foreground/70 border-border/40 hover:bg-muted hover:border-border/70'}
					{dimmed ? 'opacity-20' : ''}">AS{n.neighbour_asn}</span
			>
		{/each}
	</div>
{/snippet}

{#snippet chipGroup(items: typeof upstream)}
	{#if items.length > 18}
		<ScrollArea.Root class="h-[176px] rounded-md border border-border/40" scrollbarYClasses="w-1.5">
			{@render chipList(items)}
		</ScrollArea.Root>
	{:else}
		<div class="rounded-md border border-border/40">{@render chipList(items)}</div>
	{/if}
{/snippet}

{#snippet peerColumn(title: string, items: typeof upstream, group: 'up' | 'down' | 'lat')}
	<div class="min-w-0">
		<div class="flex items-center justify-between mb-1.5">
			<span class="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground/70"
				>{title} · {items.length}</span
			>
			{@render copyAllBtn(group)}
		</div>
		{@render chipGroup(items)}
	</div>
{/snippet}

<div class="bgp-topology" bind:this={topologyEl}>
	<!-- proportion bar -->
	{#if totalNeighbours > 0}
		<div class="px-3 pt-3 pb-2 space-y-1.5">
			<div class="h-1 rounded-full bg-border/40 flex gap-px overflow-hidden">
				{#if upstream.length > 0}
					<div class="h-full rounded-full bg-foreground/55" style="width: {upPct}%"></div>
				{/if}
				{#if downstream.length > 0}
					<div class="h-full rounded-full bg-foreground/30" style="width: {downPct}%"></div>
				{/if}
				{#if uncertain.length > 0}
					<div class="h-full rounded-full bg-foreground/15" style="width: {latPct}%"></div>
				{/if}
			</div>
			<div class="flex justify-between text-[10px] font-mono text-muted-foreground/60">
				<span class="flex items-center gap-1">
					<span class="h-[5px] w-[5px] rounded-full bg-foreground/55"></span>
					<span class="font-semibold text-foreground/70">{upstream.length}</span> up
				</span>
				<span class="flex items-center gap-1">
					<span class="h-[5px] w-[5px] rounded-full bg-foreground/30"></span>
					<span class="font-semibold text-foreground/70">{downstream.length}</span> down
				</span>
				<span class="flex items-center gap-1">
					<span class="h-[5px] w-[5px] rounded-full bg-foreground/15"></span>
					<span class="font-semibold text-foreground/70">{uncertain.length}</span> lateral
				</span>
			</div>
		</div>
	{/if}

	<!-- search -->
	{#if totalNeighbours > 10}
		<div class="px-3 pb-2">
			<div class="relative flex items-center">
				<Search
					class="absolute left-2.5 h-3 w-3 text-muted-foreground/50 pointer-events-none z-10"
				/>
				<Input
					bind:value={query}
					class="h-7 pl-7 pr-7 text-[10px] font-mono"
					placeholder="Find ASN…"
					aria-label="Find ASN"
					autocomplete="off"
					spellcheck="false"
				/>
				{#if query}
					<Button
						variant="ghost"
						size="icon"
						class="absolute right-1 z-10 h-5 w-5 text-muted-foreground/50 hover:text-foreground"
						aria-label="Clear search"
						onclick={() => (query = '')}
					>
						<X class="h-3 w-3" />
					</Button>
				{/if}
			</div>
			{#if matchCounts}
				<p class="text-[10px] font-mono text-muted-foreground/60 mt-1">
					<span class="font-semibold text-foreground/60">{matchCounts.total}</span> found
					{#if matchCounts.up > 0}<span> · {matchCounts.up} upstream</span>{/if}
					{#if matchCounts.down > 0}<span> · {matchCounts.down} downstream</span>{/if}
					{#if matchCounts.lat > 0}<span> · {matchCounts.lat} uncertain</span>{/if}
				</p>
			{/if}
		</div>
	{/if}

	<div class="px-3 pb-3">
		{#if bgp.as_overview}
			<div class="flex items-center gap-2 mb-2.5">
				<span class="h-1.5 w-1.5 rounded-full bg-foreground/70 shrink-0"></span>
				<span class="text-[12px] font-semibold font-mono tracking-tight"
					>AS{bgp.as_overview.asn}</span
				>
				{#if bgp.as_overview.holder}
					<span class="text-[10px] text-muted-foreground/50 truncate">{bgp.as_overview.holder}</span
					>
				{/if}
			</div>
		{/if}

		{#if totalNeighbours > 0}
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
				{#if upstream.length > 0}
					{@render peerColumn('Upstream', upstream, 'up')}
				{/if}
				{#if downstream.length > 0}
					{@render peerColumn('Downstream', downstream, 'down')}
				{/if}
				{#if uncertain.length > 0}
					{@render peerColumn('Uncertain', uncertain, 'lat')}
				{/if}
			</div>
		{/if}

		{#if positionLabel}
			<div class="mt-3 flex items-start gap-2 px-2.5 py-2 rounded-md border {INSIGHT_PANEL}">
				<Info class="h-3.5 w-3.5 shrink-0 mt-px text-muted-foreground/50" />
				<p class="text-[11px] leading-relaxed">
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
			<Collapsible.Root bind:open={showNetwork}>
				<Collapsible.Trigger
					class="flex items-center gap-1.5 w-full text-[10px] text-muted-foreground/40 hover:text-foreground/60 transition-colors py-1"
				>
					<ChevronRight
						class="h-2.5 w-2.5 transition-transform duration-150 {showNetwork ? 'rotate-90' : ''}"
					/>
					<span>Network Info ({bgp.network_info.length})</span>
				</Collapsible.Trigger>
				<Collapsible.Content>
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
				</Collapsible.Content>
			</Collapsible.Root>
		{/if}

		<!-- announced prefixes -->
		{#if bgp.announced_prefixes.length > 0}
			<Collapsible.Root bind:open={showPrefixes}>
				<Collapsible.Trigger
					class="flex items-center gap-1.5 w-full text-[10px] text-muted-foreground/40 hover:text-foreground/60 transition-colors py-1"
				>
					<ChevronRight
						class="h-2.5 w-2.5 transition-transform duration-150 {showPrefixes ? 'rotate-90' : ''}"
					/>
					<span>Announced Prefixes ({bgp.announced_prefixes.length})</span>
				</Collapsible.Trigger>
				<Collapsible.Content>
					<div class="mt-1">
						<div class="flex justify-end mb-1">
							<Button
								variant="outline"
								size="sm"
								class="h-5 gap-1 px-1.5 text-[10px] text-muted-foreground/60"
								onclick={copyPrefixes}
							>
								{#if copiedPrefixes}
									<Check class="h-2.5 w-2.5" />
									<span>Copied</span>
								{:else}
									<Copy class="h-2.5 w-2.5" />
									<span>copy all</span>
								{/if}
							</Button>
						</div>
						{#snippet prefixRows()}
							{#each bgp.announced_prefixes as pfx, i (pfx.prefix)}
								<div
									class="flex items-center gap-2 px-2.5 py-1.5 text-[11px]
									{i > 0 ? 'border-t border-border/40' : ''} hover:bg-muted/40 transition-colors"
								>
									<code
										class="font-mono text-foreground/80 flex-1"
										title="first seen {fmtDate(pfx.first_seen)} · last seen {fmtDate(
											pfx.last_seen
										)}">{pfx.prefix}</code
									>
									<span class="text-[10px] text-muted-foreground/50">v{pfx.ip_version}</span>
									<span class="font-mono tabular-nums text-[10px] text-muted-foreground/50"
										>{fmtDate(pfx.first_seen)}</span
									>
								</div>
							{/each}
						{/snippet}
						{#if bgp.announced_prefixes.length > 8}
							<ScrollArea.Root
								class="h-[200px] rounded-md border border-border/40"
								scrollbarYClasses="w-1.5"
							>
								{@render prefixRows()}
							</ScrollArea.Root>
						{:else}
							<div class="rounded-md border border-border/40">{@render prefixRows()}</div>
						{/if}
					</div>
				</Collapsible.Content>
			</Collapsible.Root>
		{/if}

		<!-- prefix overview -->
		{#if bgp.prefix_overview.length > 0}
			<Collapsible.Root bind:open={showPrefixOverview}>
				<Collapsible.Trigger
					class="flex items-center gap-1.5 w-full text-[10px] text-muted-foreground/40 hover:text-foreground/60 transition-colors py-1"
				>
					<ChevronRight
						class="h-2.5 w-2.5 transition-transform duration-150 {showPrefixOverview
							? 'rotate-90'
							: ''}"
					/>
					<span>Prefix Overview ({bgp.prefix_overview.length})</span>
				</Collapsible.Trigger>
				<Collapsible.Content>
					<div class="mt-1">
						{#snippet prefixOverviewRows()}
							{#each bgp.prefix_overview as po, i (po.prefix)}
								<div
									class="flex items-center gap-2 px-2.5 py-1.5 text-[10px]
									{i > 0 ? 'border-t border-border/10' : ''} hover:bg-accent/5 transition-colors"
								>
									<code class="font-mono text-foreground/70 shrink-0">{po.prefix}</code>
									{#if po.holder}
										<span class="text-muted-foreground/60 text-[10px] truncate flex-1"
											>{po.holder}</span
										>
									{:else}
										<span class="flex-1"></span>
									{/if}
									<span class="text-muted-foreground/60 text-[10px] shrink-0">AS{po.asn}</span>
									<span
										title={po.is_announced ? 'Announced' : 'Not announced'}
										aria-label={po.is_announced ? 'Announced' : 'Not announced'}
										class="h-1.5 w-1.5 rounded-full shrink-0 {po.is_announced
											? 'bg-foreground/40'
											: 'bg-destructive/60'}"
									></span>
								</div>
							{/each}
						{/snippet}
						{#if bgp.prefix_overview.length > 8}
							<ScrollArea.Root
								class="h-[200px] rounded-md border border-border/20"
								scrollbarYClasses="w-1.5"
							>
								{@render prefixOverviewRows()}
							</ScrollArea.Root>
						{:else}
							<div class="rounded-md border border-border/20 overflow-hidden">
								{@render prefixOverviewRows()}
							</div>
						{/if}
					</div>
				</Collapsible.Content>
			</Collapsible.Root>
		{/if}

		<!-- related prefixes -->
		{#if bgp.related_prefixes.length > 0}
			<Collapsible.Root bind:open={showRelated}>
				<Collapsible.Trigger
					class="flex items-center gap-1.5 w-full text-[10px] text-muted-foreground/40 hover:text-foreground/60 transition-colors py-1"
				>
					<ChevronRight
						class="h-2.5 w-2.5 transition-transform duration-150 {showRelated ? 'rotate-90' : ''}"
					/>
					<span>Related Prefixes ({bgp.related_prefixes.length})</span>
				</Collapsible.Trigger>
				<Collapsible.Content>
					<div class="mt-1">
						{#snippet relatedPrefixRows()}
							{#each bgp.related_prefixes as rp, i (rp.related_prefix)}
								<div
									class="flex items-center gap-2 px-2.5 py-1.5 text-[10px]
									{i > 0 ? 'border-t border-border/10' : ''} hover:bg-accent/5 transition-colors"
								>
									<code class="font-mono text-[11px] text-foreground/80 flex-1"
										>{rp.related_prefix}</code
									>
									<Badge
										variant="outline"
										class="text-[10px] h-4 px-1 text-muted-foreground border-border/60"
										>{rp.relationship}</Badge
									>
									{#if rp.origin_asn}<span class="font-mono text-muted-foreground/60 text-[10px]"
											>AS{rp.origin_asn}</span
										>{/if}
								</div>
							{/each}
						{/snippet}
						{#if bgp.related_prefixes.length > 8}
							<ScrollArea.Root
								class="h-[200px] rounded-md border border-border/20"
								scrollbarYClasses="w-1.5"
							>
								{@render relatedPrefixRows()}
							</ScrollArea.Root>
						{:else}
							<div class="rounded-md border border-border/20 overflow-hidden">
								{@render relatedPrefixRows()}
							</div>
						{/if}
					</div>
				</Collapsible.Content>
			</Collapsible.Root>
		{/if}

		<!-- abuse contacts -->
		{#if bgp.abuse_contacts.length > 0}
			<Collapsible.Root bind:open={showAbuse}>
				<Collapsible.Trigger
					class="flex items-center gap-1.5 w-full text-[10px] text-muted-foreground/40 hover:text-foreground/60 transition-colors py-1"
				>
					<ChevronRight
						class="h-2.5 w-2.5 transition-transform duration-150 {showAbuse ? 'rotate-90' : ''}"
					/>
					<span>Abuse Contacts ({bgp.abuse_contacts.length})</span>
				</Collapsible.Trigger>
				<Collapsible.Content>
					<div class="mt-1 space-y-1">
						{#each bgp.abuse_contacts as ac (ac.abuse_email + ac.resource)}
							<div class="flex items-center gap-1.5 text-[11px] group/ac">
								<Mail class="h-3 w-3 text-muted-foreground/40" />
								<span class="font-mono text-foreground/80">{ac.abuse_email}</span>
								{#if ac.resource}<span class="font-mono text-[10px] text-muted-foreground/50"
										>{ac.resource}</span
									>{/if}
								{#if ac.rir}<Badge
										variant="outline"
										class="text-[10px] h-4 px-1 text-muted-foreground border-border/60"
										>{ac.rir}</Badge
									>{/if}
								<div class="opacity-0 group-hover/ac:opacity-100 transition-opacity ml-auto">
									<CopyButton value={ac.abuse_email} />
								</div>
							</div>
						{/each}
					</div>
				</Collapsible.Content>
			</Collapsible.Root>
		{/if}
	</div>
</div>
