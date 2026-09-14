<script lang="ts">
	import Cell from './cell.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { CHECK_BY_KEY } from '$lib/config/hygiene';
	import type { HygieneSummary } from '$lib/utilities/scan-insights';

	interface Props {
		hygiene: HygieneSummary | null;
		scanId?: string | null;
		loading?: boolean;
		class?: string;
	}

	let { hygiene, scanId = null, loading = false, class: className = '' }: Props = $props();

	const TOP = 7;
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	let rows = $derived(
		(hygiene?.checks ?? [])
			.filter((c) => c.applicable > 0 && c.failing > 0)
			.map((c) => ({
				key: c.key,
				label: CHECK_BY_KEY[c.key]?.label ?? c.key.replace(/_/g, ' '),
				share: Math.round((c.failing / c.applicable) * 100),
				failing: c.failing,
				href: ROUTES.results(WEB.tab, scanId, { [WEB.queryParam]: c.query })
			}))
			.sort((a, b) => b.share - a.share)
			.slice(0, TOP)
	);
</script>

<Cell
	id="hygiene"
	title="Web hygiene"
	description="Failing share per check"
	href={ROUTES.results(WEB.tab, scanId, { [WEB.queryParam]: 'hygiene:any' })}
	hrefLabel="hygiene:any"
	loading={loading && !hygiene}
	class={className}
>
	{#if rows.length}
		<ul class="flex flex-col gap-1.5">
			{#each rows as r (r.key)}
				<li>
					<a
						href={r.href}
						class="grid grid-cols-[7.5rem_1fr_2.75rem] items-center gap-2.5 text-xs hover:text-foreground"
					>
						<span class="truncate text-muted-foreground">{r.label}</span>
						<span class="h-1.5 overflow-hidden rounded-full bg-muted">
							<span class="block h-full rounded-full bg-chart-4" style="width:{r.share}%"></span>
						</span>
						<span class="text-right font-medium tabular-nums">{r.share}%</span>
					</a>
				</li>
			{/each}
		</ul>
	{:else}
		<span class="text-sm text-muted-foreground">No failing check</span>
	{/if}
	{#snippet footer()}
		{#if hygiene}
			<span>
				{hygiene.evaluated.toLocaleString()} checked{#if hygiene.pending}
					· {hygiene.pending.toLocaleString()} pending{/if}
			</span>
		{/if}
	{/snippet}
</Cell>
