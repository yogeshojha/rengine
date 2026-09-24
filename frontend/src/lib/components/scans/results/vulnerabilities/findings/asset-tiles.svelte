<script lang="ts">
	import { SURFACE, SurfaceDimension, type ResultTab } from '$lib/config/surface';
	import { exactToken } from '$lib/utilities/scan-insights';
	import type { VulnerabilityRead } from '$lib/utilities/vulns';

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const SVC = SURFACE[SurfaceDimension.SERVICES];
	const EP = SURFACE[SurfaceDimension.ENDPOINTS];
	const SW = SURFACE[SurfaceDimension.SOFTWARE];
	const VULN = SURFACE[SurfaceDimension.VULNERABILITIES];
	const COLS: Record<number, string> = {
		1: 'sm:grid-cols-1',
		2: 'sm:grid-cols-2',
		3: 'sm:grid-cols-3',
		4: 'sm:grid-cols-4',
		5: 'sm:grid-cols-5'
	};

	interface Props {
		v: VulnerabilityRead;
		onFilter: (token: string) => void;
		onTab?: (tab: ResultTab, filter: string) => void;
		variant?: 'pills' | 'cells';
		class?: string;
	}

	let { v, onFilter, onTab, variant = 'pills', class: className = '' }: Props = $props();

	let hostToken = $derived(v.host ? exactToken('host', v.host) : '');
	let ipToken = $derived(v.ip ? exactToken('ip', v.ip) : '');
	let hostTotal = $derived(Object.values(v.host_findings ?? {}).reduce((a, n) => a + n, 0));

	let tiles = $derived(
		[
			{
				spec: VULN,
				n: hostTotal,
				label: `open on this ${WEB.noun}`,
				go: () => onFilter(hostToken)
			},
			{
				spec: SVC,
				n: v.asset?.open_ports ?? 0,
				label: `open ports on ${v.ip}`,
				go: onTab ? () => onTab(SVC.tab, ipToken) : null
			},
			{
				spec: WEB,
				n: v.asset?.names_on_ip ?? 0,
				label: `names on ${v.ip}`,
				go: onTab ? () => onTab(WEB.tab, ipToken) : null
			},
			{
				spec: EP,
				n: v.asset?.endpoints ?? 0,
				label: EP.nounPlural,
				go: onTab ? () => onTab(EP.tab, hostToken) : null
			},
			{
				spec: SW,
				n: v.asset?.software_cves ?? 0,
				label: 'inferred CVEs',
				go: onTab ? () => onTab(SW.tab, hostToken) : null
			}
		].filter((t) => t.n > 0)
	);
</script>

{#if tiles.length && variant === 'cells'}
	<div
		class="grid grid-cols-2 gap-px overflow-hidden rounded-md border bg-border {COLS[
			tiles.length
		] ?? 'sm:grid-cols-5'} {className}"
	>
		{#each tiles as t (t.label)}
			<button
				type="button"
				disabled={!t.go}
				class="flex min-w-0 flex-col items-start gap-1 bg-card px-4 py-2.5 text-left transition-colors enabled:hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none focus-visible:ring-inset"
				onclick={() => t.go?.()}
			>
				<span class="font-mono text-xl leading-6 font-semibold tabular-nums"
					>{t.n.toLocaleString()}</span
				>
				<span class="text-2xs text-muted-foreground">{t.label}</span>
			</button>
		{/each}
	</div>
{:else if tiles.length}
	<div class="flex flex-wrap gap-2 {className}">
		{#each tiles as t (t.label)}
			{@const Icon = t.spec.icon}
			<button
				type="button"
				disabled={!t.go}
				class="inline-flex items-center gap-2 rounded-md border border-border/70 px-2.5 py-1.5 text-left transition-colors enabled:hover:border-foreground/30 enabled:hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				onclick={() => t.go?.()}
			>
				<Icon class="size-3.5 text-muted-foreground" />
				<span class="font-mono text-sm font-semibold tabular-nums">{t.n.toLocaleString()}</span>
				<span class="text-xs text-muted-foreground">{t.label}</span>
			</button>
		{/each}
	</div>
{/if}
