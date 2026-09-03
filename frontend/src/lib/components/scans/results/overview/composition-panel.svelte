<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Server from '@lucide/svelte/icons/server';
	import Waypoints from '@lucide/svelte/icons/waypoints';
	import Lock from '@lucide/svelte/icons/lock';
	import Image from '@lucide/svelte/icons/image';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import PanelHead from './panel-head.svelte';
	import RankedList from './ranked-list.svelte';
	import type { RankedRow } from './ranked-list.svelte';
	import TechSheet from './tech-sheet.svelte';
	import TechIcon from '../tech-icon.svelte';
	import { isPrivateIp } from '$lib/utilities/scan-correlation';
	import { targetAssetNoun } from '$lib/types/target';
	import { exactToken, filterToken } from '$lib/utilities/scan-insights';
	import type { IconComponent } from '$lib/config/icons';
	import type { ScanRead } from '$lib/types/scan';
	import type { InsightTally, SubdomainInsights } from '$lib/utilities/scan-insights';

	interface Props {
		insights: SubdomainInsights | null;
		loading: boolean;
		scan: ScanRead;
		scanId: string;
		projectId: string;
		onFilter: (search: string) => void;
		onTab: (tab: string, filter?: string) => void;
	}

	let { insights, loading, scan, scanId, projectId, onFilter, onTab }: Props = $props();

	const TOP = 5;
	const SEED_SOURCE = 'target';
	const PRIVATE_BADGE = 'Private range';
	const CLUSTER_ICON: Record<string, IconComponent> = {
		ip: Server,
		cname: Waypoints,
		cert: Lock,
		favicon: Image
	};
	const CLUSTER_FILTER: Record<string, (v: string) => string> = {
		ip: (v) => filterToken('ip', v),
		cname: (v) => filterToken('cname', v),
		cert: (v) => exactToken('cert.cn', v),
		favicon: (v) => filterToken('favicon', v)
	};

	interface Cell {
		key: string;
		title: string;
		total: string;
		base: number;
		rows: RankedRow[];
		icon?: 'tech' | 'cluster';
		pick: (filter: string) => void;
		more?: { label: string; action: () => void };
		note?: string;
	}

	let techOpen = $state(false);

	const stat = (key: string) => insights?.surface.find((s) => s.key === key)?.value ?? 0;
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;
	const tallies = (xs: InsightTally[], field: string): RankedRow[] =>
		xs.slice(0, TOP).map((t) => ({
			key: t.name,
			label: t.name,
			count: t.count,
			filter: filterToken(field, t.name)
		}));

	let webHosts = $derived(stat('web'));
	let nounPlural = $derived(targetAssetNoun(scan.execution_config.target_type));

	let cells = $derived.by<Cell[]>(() => {
		if (!insights) return [];
		const out: Cell[] = [];

		if (insights.top_asn.length)
			out.push({
				key: 'networks',
				title: 'Hosting networks',
				total: plural(stat('asns'), 'network', 'networks'),
				base: stat('ips'),
				rows: tallies(insights.top_asn, 'org'),
				pick: (f) => onTab('ips', f),
				more: { label: 'View all addresses', action: () => onTab('ips') }
			});

		const sources = insights.sources.filter((s) => s.name !== SEED_SOURCE);
		if (sources.length)
			out.push({
				key: 'sources',
				title: 'Discovery sources',
				total: plural(sources.length, 'source', 'sources'),
				base: scan.subdomains_found,
				rows: tallies(sources, 'source'),
				pick: onFilter,
				note:
					insights.single_source > 0
						? `${insights.single_source.toLocaleString()} ${nounPlural} found by one source only`
						: `All ${nounPlural} were found by two or more sources`
			});

		if (insights.top_tech.length)
			out.push({
				key: 'tech',
				title: 'Technology stack',
				total: plural(insights.tech_total, 'technology', 'technologies'),
				base: webHosts,
				icon: 'tech',
				rows: tallies(insights.top_tech, 'tech'),
				pick: onFilter,
				more:
					insights.tech_total > TOP
						? {
								label: `View all ${insights.tech_total.toLocaleString()} technologies`,
								action: () => (techOpen = true)
							}
						: undefined
			});

		const clusters = insights.clusters.filter((c) => c.kind in CLUSTER_FILTER);
		if (clusters.length)
			out.push({
				key: 'clusters',
				title: 'Shared infrastructure',
				total: plural(clusters.length, 'group', 'groups'),
				base: scan.subdomains_found,
				icon: 'cluster',
				rows: clusters.slice(0, TOP).map((c) => ({
					key: `${c.kind}:${c.value}`,
					label: c.value,
					sub: c.reason,
					count: c.count,
					mono: true,
					meta: c.kind,
					badge: c.kind === 'ip' && isPrivateIp(c.value) ? PRIVATE_BADGE : undefined,
					filter: CLUSTER_FILTER[c.kind](c.value)
				})),
				pick: onFilter
			});

		if (insights.services.length)
			out.push({
				key: 'services',
				title: 'Exposed services',
				total: plural(stat('ports'), 'open port', 'open ports'),
				base: stat('ports'),
				rows: tallies(insights.services, 'service'),
				pick: onFilter
			});

		return out;
	});
</script>

{#if (loading && !insights) || cells.length}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Composition" />
		<div
			class="-mt-px -ml-px grid grid-cols-1 md:grid-cols-2 lg:grid-cols-[repeat(auto-fit,minmax(14rem,1fr))]"
		>
			{#if !insights}
				{#each Array(4) as _, i (i)}
					<div class="flex flex-col gap-4 border-t border-l p-5">
						<Skeleton class="h-4 w-32" />
						{#each Array(4) as _, j (j)}
							<Skeleton class="h-8 w-full" />
						{/each}
					</div>
				{/each}
			{:else}
				{#each cells as c (c.key)}
					<section class="flex min-w-0 flex-col gap-4 border-t border-l p-5">
						<div class="flex items-baseline justify-between gap-3">
							<h3 class="text-sm font-medium">{c.title}</h3>
							<span class="shrink-0 text-xs text-muted-foreground tabular-nums">{c.total}</span>
						</div>
						{#if c.icon === 'tech'}
							<RankedList rows={c.rows} base={c.base} onSelect={c.pick}>
								{#snippet icon(r)}
									<TechIcon name={r.label} class="size-4" />
								{/snippet}
							</RankedList>
						{:else if c.icon === 'cluster'}
							<RankedList rows={c.rows} base={c.base} onSelect={c.pick}>
								{#snippet icon(r)}
									{@const Icon = CLUSTER_ICON[r.meta ?? ''] ?? Server}
									<Icon class="size-4 text-muted-foreground" />
								{/snippet}
							</RankedList>
						{:else}
							<RankedList rows={c.rows} base={c.base} onSelect={c.pick} />
						{/if}
						{#if c.more}
							{@const more = c.more}
							<Button
								variant="link"
								size="sm"
								class="mt-auto h-auto gap-1 self-start px-0 text-xs"
								onclick={more.action}
							>
								{more.label}
								<ChevronRight class="size-3.5" />
							</Button>
						{:else if c.note}
							<p class="mt-auto pt-1 text-xs text-muted-foreground">{c.note}</p>
						{/if}
					</section>
				{/each}
			{/if}
		</div>
	</Card.Root>
{/if}

{#if insights}
	<TechSheet
		bind:open={techOpen}
		total={insights.tech_total}
		hosts={webHosts}
		{scanId}
		{projectId}
		onPick={(name) => onFilter(filterToken('tech', name))}
	/>
{/if}
