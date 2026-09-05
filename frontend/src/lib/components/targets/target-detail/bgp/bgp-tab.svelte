<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import Copy from '@lucide/svelte/icons/copy';
	import Check from '@lucide/svelte/icons/check';
	import { toast } from 'svelte-sonner';
	import { SvelteSet } from 'svelte/reactivity';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import RecordShell from '../record-shell.svelte';
	import RecordGroup from '../record-group.svelte';
	import { TargetType } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import type { TargetBgpDetailResponse } from '$lib/types/target-detail';
	import {
		PEER_RELATIONSHIP_LABELS,
		PREFIX_RELATIONSHIP_LABELS,
		type PeerRelationship
	} from '$lib/types/ripestat';
	import { formatShortDate } from '$lib/utilities/dates';
	import { writeClipboard } from '$lib/utilities/clipboard';

	interface Props {
		targetValue: string;
		targetType: TargetType;
		bgp: TargetBgpDetailResponse | null;
		status: TaskStatus;
		loading: boolean;
		refreshing: boolean;
		onRefresh: () => void;
	}

	let { targetValue, targetType, bgp, status, loading, refreshing, onRefresh }: Props = $props();

	const VALID_RIR = /^(arin|ripe|apnic|lacnic|afrinic)/i;
	const PREFIX_PAGE = 100;
	const PEER_PAGE = 60;
	const PEER_GROUPS: PeerRelationship[] = ['upstream', 'downstream', 'uncertain'];
	const FAMILIES = ['all', '4', '6'] as const;
	type Family = (typeof FAMILIES)[number];
	const ROW =
		'grid grid-cols-[7rem_minmax(0,1fr)] items-start gap-x-3 py-1.5 sm:grid-cols-[9rem_minmax(0,1fr)]';

	let isAsn = $derived(targetType === TargetType.ASN);
	let isRange = $derived(targetType === TargetType.IP_RANGE);
	let as = $derived(bgp?.as_overview ?? null);
	let rir = $derived((as?.rir && VALID_RIR.test(as.rir) ? as.rir : '').toUpperCase());
	let prefixes = $derived(bgp?.announced_prefixes ?? []);
	let neighbours = $derived(bgp?.neighbours ?? []);
	let networkInfo = $derived(bgp?.network_info?.[0] ?? null);
	let prefixOverview = $derived(bgp?.prefix_overview?.[0] ?? null);
	let relatedPrefixes = $derived(bgp?.related_prefixes ?? []);
	let abuse = $derived(bgp?.abuse_contacts ?? []);
	let hasData = $derived(
		!!as || prefixes.length > 0 || neighbours.length > 0 || !!networkInfo || !!prefixOverview
	);
	let headline = $derived.by(() => {
		if (!bgp) return targetValue;
		if (isAsn) return as ? `AS${as.asn} · ${as.holder}` : targetValue;
		const asn = networkInfo?.asn ?? prefixOverview?.asn ?? as?.asn;
		const parts = [targetValue];
		if (asn) parts.push(`AS${asn}`);
		if (as?.holder) parts.push(as.holder);
		return parts.join(' · ');
	});

	interface Fact {
		key: string;
		label: string;
		value: string;
		sub?: string;
		mono?: boolean;
		copy?: string;
		tone?: 'warn';
	}
	let facts = $derived.by<Fact[]>(() => {
		if (!bgp) return [];
		const out: Fact[] = [];
		const v4 = prefixes.filter((p) => p.ip_version === 4).length;
		const v6 = prefixes.length - v4;
		const up = neighbours.filter((n) => n.relationship === 'upstream').length;
		const down = neighbours.filter((n) => n.relationship === 'downstream').length;
		if (isAsn) {
			if (as?.holder) out.push({ key: 'holder', label: 'Holder', value: as.holder });
			if (as)
				out.push({
					key: 'announced',
					label: 'Status',
					value: as.announced ? 'Announced' : 'Not announced',
					tone: as.announced ? undefined : 'warn'
				});
			if (rir) out.push({ key: 'rir', label: 'Registry', value: rir });
			if (prefixes.length)
				out.push({
					key: 'prefixes',
					label: 'Prefixes',
					value: prefixes.length.toLocaleString(),
					sub: `${v4.toLocaleString()} IPv4 · ${v6.toLocaleString()} IPv6`
				});
			if (neighbours.length)
				out.push({
					key: 'peers',
					label: 'Peers',
					value: neighbours.length.toLocaleString(),
					sub: `${up.toLocaleString()} upstream · ${down.toLocaleString()} downstream`
				});
			if (as?.block_resource)
				out.push({
					key: 'block',
					label: 'Allocation block',
					value: as.block_resource,
					sub: as.block_name ?? undefined,
					mono: true
				});
		} else {
			const prefix = networkInfo?.prefix ?? prefixOverview?.prefix ?? '';
			const asn = networkInfo?.asn ?? prefixOverview?.asn ?? as?.asn;
			const holder = as?.holder ?? prefixOverview?.holder ?? '';
			if (!isRange)
				out.push({
					key: 'address',
					label: 'Address',
					value: targetValue,
					mono: true,
					copy: targetValue
				});
			if (prefix)
				out.push({
					key: 'prefix',
					label: isRange ? 'Prefix' : 'Covering prefix',
					value: prefix,
					mono: true,
					copy: prefix
				});
			if (asn)
				out.push({
					key: 'asn',
					label: 'Origin AS',
					value: `AS${asn}`,
					sub: holder || undefined,
					mono: true,
					copy: `AS${asn}`
				});
			if (rir) out.push({ key: 'rir', label: 'Registry', value: rir });
			const announced = prefixOverview?.is_announced ?? (networkInfo ? true : as?.announced);
			if (announced != null)
				out.push({
					key: 'announced',
					label: 'Status',
					value: announced ? 'Announced' : 'Not announced',
					tone: announced ? undefined : 'warn'
				});
		}
		return out;
	});

	let prefixQuery = $state('');
	let prefixFamily = $state<Family>('all');
	let prefixShown = $state(PREFIX_PAGE);
	let prefixRows = $derived.by(() => {
		const q = prefixQuery.trim().toLowerCase();
		return prefixes
			.filter((p) => prefixFamily === 'all' || String(p.ip_version) === prefixFamily)
			.filter((p) => !q || p.prefix.toLowerCase().includes(q))
			.sort((a, b) => a.ip_version - b.ip_version || a.prefix.localeCompare(b.prefix));
	});
	$effect(() => {
		void prefixQuery;
		void prefixFamily;
		prefixShown = PREFIX_PAGE;
	});
	let copiedPrefixes = $state(false);
	async function copyPrefixes() {
		if (!(await writeClipboard(prefixRows.map((p) => p.prefix).join('\n')))) {
			toast.error('Could not copy');
			return;
		}
		copiedPrefixes = true;
		setTimeout(() => (copiedPrefixes = false), 1500);
	}

	let peerQuery = $state('');
	let peerExpanded = new SvelteSet<string>();
	let peerGroups = $derived.by(() => {
		const q = peerQuery.trim().replace(/^as/i, '');
		return PEER_GROUPS.map((rel) => {
			const all = neighbours
				.filter((n) => n.relationship === rel)
				.sort((a, b) => (b.power ?? 0) - (a.power ?? 0) || a.neighbour_asn - b.neighbour_asn);
			const items = q ? all.filter((n) => String(n.neighbour_asn).includes(q)) : all;
			return { rel, label: PEER_RELATIONSHIP_LABELS[rel], total: all.length, items };
		}).filter((g) => g.total > 0);
	});
	const familyLabel = (f: Family) => (f === 'all' ? 'All' : f === '4' ? 'IPv4' : 'IPv6');
	const familyCount = (f: Family) =>
		f === 'all' ? prefixes.length : prefixes.filter((p) => String(p.ip_version) === f).length;
</script>

<RecordShell
	name="BGP"
	{status}
	queriedAt={bgp?.summary?.queried_at ?? null}
	{refreshing}
	{loading}
	empty={!hasData}
	emptyText="No routing data. The resource is not visible in the global routing table, or the lookup has not run."
	{onRefresh}
>
	{#snippet bar()}
		<span class="text-[13px]">
			<span class="font-medium">Routing</span>
			<span class="text-muted-foreground"> · {headline}</span>
		</span>
	{/snippet}

	<div class="flex flex-col">
		<RecordGroup label="Routing" mono={false}>
			{#each facts as f (f.key)}
				<div class="group {ROW}">
					<span class="pt-px text-xs text-muted-foreground">{f.label}</span>
					<span
						class="flex min-w-0 flex-col text-[13px] leading-5 {f.tone === 'warn'
							? 'text-warning'
							: ''}"
					>
						<span class="flex min-w-0 items-center gap-1.5">
							<span class="min-w-0 wrap-anywhere {f.mono ? 'font-mono text-[12.5px]' : ''}">
								{f.value}
							</span>
							{#if f.copy}
								<span
									class="flex h-4 shrink-0 items-center opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100"
								>
									<CopyButton value={f.copy} class="size-5" />
								</span>
							{/if}
						</span>
						{#if f.sub}<span class="text-xs text-muted-foreground">{f.sub}</span>{/if}
					</span>
				</div>
			{/each}
		</RecordGroup>

		{#if prefixes.length}
			<RecordGroup label="Prefixes" mono={false} sub="{prefixes.length.toLocaleString()} announced">
				<div class="flex flex-wrap items-center gap-x-3 gap-y-2 py-2">
					<div class="flex items-center gap-0.5">
						{#each FAMILIES as f (f)}
							<button
								type="button"
								class="rounded-md px-2 py-1 text-[13px] {prefixFamily === f
									? 'bg-muted font-medium'
									: 'text-muted-foreground hover:text-foreground'}"
								onclick={() => (prefixFamily = f)}
							>
								{familyLabel(f)}
								<span class="ml-1 text-[11px] tabular-nums">{familyCount(f).toLocaleString()}</span>
							</button>
						{/each}
					</div>
					<div class="relative">
						<Search
							class="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
						/>
						<Input
							bind:value={prefixQuery}
							placeholder="Find prefix"
							aria-label="Find prefix"
							class="h-8 w-44 pl-8 font-mono text-xs"
						/>
					</div>
					<Button variant="outline" size="sm" class="ml-auto h-8 gap-1.5" onclick={copyPrefixes}>
						{#if copiedPrefixes}
							<Check class="size-3.5" /> Copied
						{:else}
							<Copy class="size-3.5" />
							Copy {prefixRows.length === prefixes.length
								? 'all'
								: prefixRows.length.toLocaleString()}
						{/if}
					</Button>
				</div>
				{#if prefixRows.length === 0}
					<p class="py-6 text-center text-sm text-muted-foreground">No prefix matches.</p>
				{:else}
					{#each prefixRows.slice(0, prefixShown) as p (p.prefix)}
						<div class="group flex items-center gap-3 py-1.5 text-[13px]">
							<code class="min-w-0 flex-1 font-mono text-[12.5px]">{p.prefix}</code>
							<span
								class="hidden w-24 shrink-0 text-right text-xs text-muted-foreground tabular-nums sm:block"
							>
								{p.first_seen ? formatShortDate(p.first_seen) : '—'}
							</span>
							<span
								class="hidden w-24 shrink-0 text-right text-xs text-muted-foreground tabular-nums sm:block"
							>
								{p.last_seen ? formatShortDate(p.last_seen) : '—'}
							</span>
							<span
								class="flex h-4 shrink-0 items-center opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100"
							>
								<CopyButton value={p.prefix} class="size-5" />
							</span>
						</div>
					{/each}
					{#if prefixRows.length > prefixShown}
						<div class="py-2">
							<Button
								variant="ghost"
								size="sm"
								class="h-7 text-xs text-muted-foreground"
								onclick={() => (prefixShown += PREFIX_PAGE)}
							>
								Show {Math.min(PREFIX_PAGE, prefixRows.length - prefixShown).toLocaleString()} more of
								{(prefixRows.length - prefixShown).toLocaleString()}
							</Button>
						</div>
					{/if}
				{/if}
			</RecordGroup>
		{/if}

		{#if neighbours.length}
			<RecordGroup label="Peers" mono={false} sub="{neighbours.length.toLocaleString()} neighbours">
				<div class="flex items-center gap-3 py-2">
					<div class="relative">
						<Search
							class="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
						/>
						<Input
							bind:value={peerQuery}
							placeholder="Find AS"
							aria-label="Find AS number"
							class="h-8 w-40 pl-8 font-mono text-xs"
						/>
					</div>
				</div>
				<div class="grid grid-cols-1 gap-x-6 gap-y-4 py-2 md:grid-cols-3">
					{#each peerGroups as g (g.rel)}
						{@const open = peerExpanded.has(g.rel)}
						{@const shown = open ? g.items : g.items.slice(0, PEER_PAGE)}
						{@const more = g.items.length - shown.length}
						<div class="flex min-w-0 flex-col gap-2">
							<div class="flex items-baseline justify-between gap-3 text-[13px]">
								<span class="font-medium">{g.label}</span>
								<span class="text-xs text-muted-foreground tabular-nums">
									{peerQuery.trim() && g.items.length !== g.total
										? `${g.items.length.toLocaleString()} of ${g.total.toLocaleString()}`
										: g.total.toLocaleString()}
								</span>
							</div>
							{#if shown.length === 0}
								<span class="text-xs text-muted-foreground">No match</span>
							{:else}
								<div class="flex flex-wrap gap-1.5">
									{#each shown as n (n.neighbour_asn)}
										<Hint
											text="{n.power.toLocaleString()} observed {n.power === 1 ? 'path' : 'paths'}"
										>
											{#snippet child(props)}
												<span
													{...props}
													class="inline-flex h-6 items-center rounded-md border bg-muted/40 px-2 font-mono text-xs tabular-nums"
												>
													AS{n.neighbour_asn}
												</span>
											{/snippet}
										</Hint>
									{/each}
									{#if more > 0}
										<button
											type="button"
											class="inline-flex h-6 items-center rounded-md border border-dashed px-2 text-xs text-muted-foreground hover:text-foreground"
											onclick={() => peerExpanded.add(g.rel)}
										>
											+{more.toLocaleString()} more
										</button>
									{/if}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			</RecordGroup>
		{/if}

		{#if relatedPrefixes.length}
			<RecordGroup label="Related prefixes" mono={false} sub="{relatedPrefixes.length} overlapping">
				{#each relatedPrefixes as r (`${r.related_prefix}-${r.relationship}`)}
					<div class="group flex items-center gap-3 py-1.5 text-[13px]">
						<code class="min-w-0 flex-1 font-mono text-[12.5px]">{r.related_prefix}</code>
						<span class="shrink-0 text-xs text-muted-foreground">
							{PREFIX_RELATIONSHIP_LABELS[r.relationship] ?? r.relationship}
						</span>
						<span class="w-20 shrink-0 text-right font-mono text-xs text-muted-foreground">
							{r.origin_asn ? `AS${r.origin_asn}` : '—'}
						</span>
						<span
							class="flex h-4 shrink-0 items-center opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100"
						>
							<CopyButton value={r.related_prefix} class="size-5" />
						</span>
					</div>
				{/each}
			</RecordGroup>
		{/if}

		{#if abuse.length}
			<RecordGroup label="Abuse contacts" mono={false} sub="from the registry">
				{#each abuse as a (`${a.resource}-${a.abuse_email}`)}
					<div class="group flex items-center gap-3 py-1.5 text-[13px]">
						<code class="w-36 shrink-0 truncate font-mono text-xs text-muted-foreground">
							{a.resource}
						</code>
						<code class="min-w-0 flex-1 font-mono text-[12.5px] wrap-anywhere">{a.abuse_email}</code
						>
						{#if a.rir}<span class="shrink-0 text-xs text-muted-foreground uppercase">{a.rir}</span
							>{/if}
						<span
							class="flex h-4 shrink-0 items-center opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100"
						>
							<CopyButton value={a.abuse_email} class="size-5" />
						</span>
					</div>
				{/each}
			</RecordGroup>
		{/if}
	</div>
</RecordShell>
