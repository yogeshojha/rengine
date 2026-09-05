<script lang="ts">
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import Flame from '@lucide/svelte/icons/flame';
	import Plug from '@lucide/svelte/icons/plug';
	import Check from '@lucide/svelte/icons/check';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Spinner } from '$lib/components/ui/spinner';
	import SectionHead from '../section-head.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { IconComponent } from '$lib/config/icons';
	import { formatShortDate } from '$lib/utilities/dates';
	import type { TargetSummaryRead } from '$lib/types/target-summary';
	import type { Check as PostureCheck } from './derive';

	interface Props {
		summary: TargetSummaryRead | null;
		checks: PostureCheck[];
		loading: boolean;
		onTab: (tab: string) => void;
	}

	let { summary, checks, loading, onTab }: Props = $props();

	type Tone = 'critical' | 'warning' | 'info';
	interface Tile {
		key: string;
		tone: Tone;
		icon: IconComponent;
		count?: string;
		unit?: string;
		label: string;
		detail?: string;
		href?: string;
		tab?: string;
		pending?: boolean;
	}

	const VULNS = SURFACE[SurfaceDimension.VULNERABILITIES];
	const SERVICES = SURFACE[SurfaceDimension.SERVICES];
	const RANK: Record<Tone, number> = { critical: 0, warning: 1, info: 2 };
	const TONE = {
		critical: { ic: 'bg-destructive/10 text-destructive', dot: 'bg-destructive' },
		warning: { ic: 'bg-warning/12 text-warning', dot: 'bg-warning' },
		info: { ic: 'bg-info/10 text-info', dot: 'bg-info' }
	};

	const TILE = 'flex min-w-0 flex-col gap-2.5 rounded-[10px] border p-3 text-left';
	const TILE_LINK = `${TILE} cursor-pointer transition-colors hover:border-primary/40 hover:bg-accent/40`;

	let risk = $derived(summary?.risk ?? null);
	let tiles = $derived.by<Tile[]>(() => {
		const out: Tile[] = [];
		if (risk?.scan_id) {
			const critical = risk.by_severity.find((s) => s.severity === 'critical')?.count ?? 0;
			const high = risk.by_severity.find((s) => s.severity === 'high')?.count ?? 0;
			const vuln = (q: string) =>
				ROUTES.scanTab(risk!.scan_id!, VULNS.tab, { [VULNS.queryParam]: q });
			if (critical)
				out.push({
					key: 'critical',
					tone: 'critical',
					icon: ShieldAlert,
					count: critical.toLocaleString(),
					label: critical === 1 ? 'Critical finding' : 'Critical findings',
					detail: high ? `${high.toLocaleString()} high beside them` : undefined,
					href: vuln('severity:critical')
				});
			else if (high)
				out.push({
					key: 'high',
					tone: 'critical',
					icon: ShieldAlert,
					count: high.toLocaleString(),
					label: high === 1 ? 'High finding' : 'High findings',
					href: vuln('severity:high')
				});
			if (risk.kev)
				out.push({
					key: 'kev',
					tone: 'critical',
					icon: Flame,
					count: risk.kev.toLocaleString(),
					label: 'Known exploited',
					detail: 'Listed in CISA KEV, fix first',
					href: vuln('is:kev')
				});
			if (!critical && !high && risk.actionable)
				out.push({
					key: 'actionable',
					tone: 'warning',
					icon: ShieldAlert,
					count: risk.actionable.toLocaleString(),
					label: risk.actionable === 1 ? 'Medium finding' : 'Medium findings',
					href: vuln('severity:medium')
				});
		}
		const sensitive = summary?.sensitive_services ?? 0;
		const servicesScan = summary?.surface.find((m) => m.key === SurfaceDimension.SERVICES)?.scan_id;
		if (sensitive && servicesScan)
			out.push({
				key: 'sensitive',
				tone: 'warning',
				icon: Plug,
				count: sensitive.toLocaleString(),
				label: sensitive === 1 ? 'Sensitive service' : 'Sensitive services',
				detail: 'Databases, remote access and admin ports open',
				href: ROUTES.scanTab(servicesScan, SERVICES.tab, { [SERVICES.queryParam]: 'is:sensitive' })
			});
		for (const c of checks) {
			if (c.status === 'pass' || c.status === 'info') continue;
			out.push({
				key: c.key,
				tone: c.status === 'fail' ? 'critical' : c.status === 'pending' ? 'info' : 'warning',
				icon: c.icon,
				count: c.count,
				unit: c.unit,
				label: c.label,
				detail: c.detail,
				tab: c.tab,
				pending: c.status === 'pending'
			});
		}
		return out.sort((a, b) => RANK[a.tone] - RANK[b.tone]);
	});
	let quiet = $derived(checks.filter((c) => c.status === 'pass' || c.status === 'info'));
	let observed = $derived(risk?.observed_at ? formatShortDate(risk.observed_at) : null);
	let sub = $derived.by(() => {
		const parts: string[] = [];
		if (risk?.scan_id && observed) parts.push(`findings from the ${observed} run`);
		if (risk?.suppressed) parts.push(`${risk.suppressed.toLocaleString()} suppressed by review`);
		return parts.join(' · ');
	});
</script>

{#snippet tile(t: Tile)}
	{@const Icon = t.icon}
	{@const tone = TONE[t.tone]}
	<span class="flex size-[30px] items-center justify-center rounded-lg {tone.ic}">
		{#if t.pending}<Spinner class="size-3.5" />{:else}<Icon class="size-3.5" />{/if}
	</span>
	{#if t.count}
		<span class="text-[22px] leading-none font-semibold tracking-tight tabular-nums">
			{t.count}{#if t.unit}<span class="ml-1 text-[13px] font-medium tracking-normal">{t.unit}</span
				>{/if}
		</span>
	{/if}
	<span class="flex items-center gap-1.5 text-[13px] leading-tight font-medium">
		<span class="size-1.5 shrink-0 rounded-full {tone.dot}" aria-hidden="true"></span>
		{t.label}
	</span>
	{#if t.detail}
		<span class="text-xs leading-snug text-muted-foreground wrap-anywhere">{t.detail}</span>
	{/if}
{/snippet}

{#if loading || tiles.length || quiet.length}
	<section class="flex flex-col gap-3 border-t py-5">
		<SectionHead
			title="Needs attention"
			count={tiles.length || (quiet.length && !loading ? 'Nothing to review' : null)}
		>
			{#if sub}<span>{sub}</span>{/if}
		</SectionHead>

		{#if loading && !tiles.length && !quiet.length}
			<div class="grid grid-cols-2 gap-2 lg:grid-cols-4">
				{#each Array(4) as _, i (i)}
					<Skeleton class="h-28 rounded-[10px]" />
				{/each}
			</div>
		{:else}
			{#if tiles.length}
				<div class="grid grid-cols-2 gap-2 lg:grid-cols-4">
					{#each tiles as t (t.key)}
						{#if t.href}
							<a href={t.href} class={TILE_LINK}>{@render tile(t)}</a>
						{:else if t.tab}
							<button type="button" class={TILE_LINK} onclick={() => onTab(t.tab!)}>
								{@render tile(t)}
							</button>
						{:else}
							<div class={TILE}>{@render tile(t)}</div>
						{/if}
					{/each}
				</div>
			{/if}
			{#if quiet.length}
				<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
					{#each quiet as c (c.key)}
						<button
							type="button"
							class="flex items-center gap-1.5 {c.tab
								? 'cursor-pointer hover:text-foreground'
								: 'cursor-default'}"
							disabled={!c.tab}
							onclick={() => c.tab && onTab(c.tab)}
						>
							{#if c.status === 'pass'}
								<Check class="size-3 text-success" />
							{:else}
								<span class="size-1 rounded-full bg-muted-foreground/60" aria-hidden="true"></span>
							{/if}
							{c.label}{#if c.detail && c.status === 'info'}<span class="text-muted-foreground/70">
									· {c.detail}</span
								>{/if}
						</button>
					{/each}
				</div>
			{/if}
		{/if}
	</section>
{/if}
