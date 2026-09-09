<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Widget from './widget.svelte';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import ServiceIcon from '$lib/components/scans/results/services/service-icon.svelte';
	import { interestCatalog } from '$lib/stores/interest-catalog.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { BAND_RAIL, KIND_ICONS } from '$lib/config/interest';
	import { FEED_QUERIES, type DashboardFeed } from '$lib/types/dashboard';

	interface Props {
		feed: DashboardFeed | null;
		class?: string;
	}

	let { feed, class: className = '' }: Props = $props();

	const VULNS = SURFACE[SurfaceDimension.VULNERABILITIES];
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const SERVICES = SURFACE[SurfaceDimension.SERVICES];
	const ENDPOINTS = SURFACE[SurfaceDimension.ENDPOINTS];
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	$effect(() => {
		void interestCatalog.load();
	});

	let sections = $derived.by(() => {
		if (!feed) return [];
		return [
			{
				key: 'vulns',
				spec: VULNS,
				label: 'Findings',
				total: feed.vulns.total,
				href: ROUTES.surface(VULNS.tab, { [VULNS.queryParam]: 'is:new' })
			},
			{
				key: 'exposures',
				spec: WEB,
				label: 'Exposed hosts',
				total: feed.exposures.total,
				href: ROUTES.exposures()
			},
			{
				key: 'services',
				spec: SERVICES,
				label: 'Sensitive services',
				total: feed.services.total,
				href: ROUTES.surface(SERVICES.tab, { [SERVICES.queryParam]: FEED_QUERIES.services })
			},
			{
				key: 'endpoints',
				spec: ENDPOINTS,
				label: 'Live endpoints taking input',
				total: feed.endpoints.total,
				href: ROUTES.surface(ENDPOINTS.tab, { [ENDPOINTS.queryParam]: FEED_QUERIES.endpoints })
			}
		].filter((s) => s.total > 0);
	});
</script>

<Widget
	title="New since the previous scan"
	description="What the latest run of each target reported for the first time"
	class={className}
>
	<div class="divide-y divide-border/60">
		{#each sections as s (s.key)}
			<section class="flex flex-col gap-1 px-5 py-3">
				<a
					href={s.href}
					class="flex items-center gap-1.5 text-[11px] font-medium tracking-wider text-muted-foreground uppercase hover:text-foreground"
				>
					<s.spec.icon class="size-3.5" />
					{s.label}
					<span class="text-success tabular-nums normal-case">▲ {s.total.toLocaleString()}</span>
					<ArrowUpRight class="ml-auto size-3" />
				</a>
				<ul class="flex flex-col">
					{#if s.key === 'vulns' && feed}
						{#each feed.vulns.items as v (v.id)}
							<li>
								<a
									href={ROUTES.scanTab(v.scan_id, VULNS.tab, {
										[VULNS.queryParam]: `template=${JSON.stringify(v.template_id)}`
									})}
									class="flex items-center gap-2 py-1 text-sm hover:text-foreground"
								>
									<SeverityMark severity={v.severity} size="sm" />
									<span class="min-w-0 flex-1 truncate">{v.template_name}</span>
									<span class="max-w-[40%] truncate font-mono text-xs text-muted-foreground">
										{v.host ?? v.matched_at}
									</span>
								</a>
							</li>
						{/each}
					{:else if s.key === 'exposures' && feed}
						{#each feed.exposures.rows as r (r.subdomain_id)}
							{@const Icon = KIND_ICONS[r.kinds[0] ?? '']}
							<li>
								<a
									href={ROUTES.exposures()}
									class="flex items-center gap-2 py-1 text-sm hover:text-foreground"
								>
									<span class="h-4 w-0.5 shrink-0 rounded-full {BAND_RAIL[r.band] ?? 'bg-muted'}"
									></span>
									<span class="min-w-0 flex-1 truncate font-mono text-xs">{r.host}</span>
									{#if r.kinds[0]}
										<span class="flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
											{#if Icon}<Icon class="size-3" />{/if}
											{interestCatalog.kind(r.kinds[0])?.label ?? r.kinds[0]}
										</span>
									{/if}
								</a>
							</li>
						{/each}
					{:else if s.key === 'services' && feed}
						{#each feed.services.items as svc (svc.id)}
							<li>
								<a
									href={ROUTES.surface(SERVICES.tab, {
										[SERVICES.queryParam]: `ip=${svc.ip} port=${svc.port}`
									})}
									class="flex items-center gap-2 py-1 text-sm hover:text-foreground"
								>
									<ServiceIcon
										service={svc.service_name}
										serviceClass={svc.service_class}
										class="size-4 shrink-0"
									/>
									<span class="min-w-0 flex-1 truncate font-mono text-xs">{svc.ip}:{svc.port}</span>
									<span class="shrink-0 text-xs text-muted-foreground">
										{svc.service_name ?? svc.description}
									</span>
								</a>
							</li>
						{/each}
					{:else if s.key === 'endpoints' && feed}
						{#each feed.endpoints.items as e (e.id)}
							<li>
								<a
									href={ROUTES.surface(ENDPOINTS.tab, {
										ep_host: e.host,
										ep_q: `path=${JSON.stringify(e.path)}`
									})}
									class="flex items-center gap-2 py-1 text-sm hover:text-foreground"
								>
									<span class="min-w-0 flex-1 truncate font-mono text-xs">
										<span class="text-muted-foreground">{e.host}</span>{e.path}
									</span>
									{#if e.param_count}
										<span class="shrink-0 font-mono text-[11px] text-primary">
											?{e.params.slice(0, 2).join('&')}{e.params.length > 2 ? '…' : ''}
										</span>
									{/if}
								</a>
							</li>
						{/each}
					{/if}
				</ul>
			</section>
		{/each}
	</div>
	{#snippet footer()}
		{#if feed}
			{plural(
				feed.vulns.total + feed.exposures.total + feed.services.total + feed.endpoints.total,
				'new item',
				'new items'
			)} judged against each target's own previous run
		{/if}
	{/snippet}
</Widget>
