<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	import Cell from './cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { EVIDENCE_LABELS, EVIDENCE_ORDER } from '$lib/config/evidence';
	import { SEVERITY_LABELS, SEVERITY_ORDER } from '$lib/config/vulnerabilities';
	import type { DashboardRisk } from '$lib/types/dashboard';

	interface Props {
		risk: DashboardRisk;
		class?: string;
	}

	let { risk, class: className = '' }: Props = $props();

	const VULN = SURFACE[SurfaceDimension.VULNERABILITIES];
	const SEVERITIES = SEVERITY_ORDER.filter((s) => s !== 'unknown');
	const RUNGS = EVIDENCE_ORDER.filter((r) => r !== 'inferred');

	let cells = $derived.by(() => {
		const map = new SvelteMap<string, number>();
		for (const c of risk.evidence) map.set(`${c.severity}:${c.evidence}`, c.count);
		return map;
	});
	let max = $derived(Math.max(1, ...risk.evidence.map((c) => c.count)));
	let proven = $derived(
		risk.evidence.filter((c) => c.evidence === 'proven').reduce((n, c) => n + c.count, 0)
	);
	const wash = (n: number) =>
		n
			? `color-mix(in oklch, var(--series) ${8 + Math.round(Math.sqrt(n / max) * 58)}%, var(--muted))`
			: 'var(--muted)';
	const link = (sev: string, rung: string) =>
		ROUTES.surface(VULN.tab, { [VULN.queryParam]: `severity:${sev} and evidence:${rung}` });
</script>

<Cell
	id="evidence"
	title="Evidence"
	description="Findings by severity and rung"
	href={ROUTES.surface(VULN.tab, { [VULN.queryParam]: 'evidence:proven' })}
	hrefLabel="evidence:proven"
	class={className}
>
	<div
		class="grid gap-1 text-2xs text-muted-foreground"
		style="grid-template-columns:4rem repeat({RUNGS.length},1fr)"
	>
		<span></span>
		{#each RUNGS as r (r)}
			<span class="text-center leading-tight">{EVIDENCE_LABELS[r]}</span>
		{/each}
		{#each SEVERITIES as sev (sev)}
			<span class="flex items-center">{SEVERITY_LABELS[sev]}</span>
			{#each RUNGS as r (r)}
				{@const n = cells.get(`${sev}:${r}`) ?? 0}
				<Hint
					text={n
						? `${n.toLocaleString()} ${SEVERITY_LABELS[sev].toLowerCase()} · ${EVIDENCE_LABELS[r].toLowerCase()}`
						: ''}
				>
					{#snippet child(props)}
						<a
							{...props}
							href={n ? link(sev, r) : undefined}
							class="flex h-7 items-center justify-center rounded-md text-xs font-medium text-foreground tabular-nums transition-shadow {n
								? 'hover:ring-1 hover:ring-ring'
								: ''}"
							style="background:{wash(n)}"
							aria-label="{SEVERITY_LABELS[sev]} {EVIDENCE_LABELS[r]}: {n}"
						>
							{n || ''}
						</a>
					{/snippet}
				</Hint>
			{/each}
		{/each}
	</div>
	{#snippet footer()}
		<span>
			{proven.toLocaleString()} proven
		</span>
	{/snippet}
</Cell>
