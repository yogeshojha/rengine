<script lang="ts">
	import { useScopedRoutes } from './scope-links';
	import Cell from './cell.svelte';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { CERT_BUCKET_FILL } from '$lib/config/dashboard';
	import type { DashboardCertBucket } from '$lib/types/dashboard';

	const routes = useScopedRoutes();

	interface Props {
		buckets: DashboardCertBucket[];
		expiringQuery: string;
		scanId?: string | null;
		class?: string;
	}

	let { buckets, expiringQuery, scanId = null, class: className = '' }: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	let max = $derived(Math.max(1, ...buckets.map((b) => b.count)));
	let total = $derived(buckets.reduce((n, b) => n + b.count, 0));
	const link = (q: string) => routes.results(WEB.tab, scanId, { [WEB.queryParam]: q });
</script>

<Cell
	id="certs"
	description="Live web assets by days to expiry"
	href={link(expiringQuery)}
	hrefLabel={expiringQuery}
	class={className}
>
	<div class="grid min-h-28 auto-cols-fr grid-flow-col grid-rows-[1fr_auto] gap-x-2 gap-y-1">
		{#each buckets as b (b.key)}
			<a
				href={link(b.query)}
				class="group row-span-2 grid min-w-0 grid-rows-subgrid"
				aria-label="{b.label}: {b.count}"
			>
				<span class="flex flex-col items-center justify-end gap-1">
					<span class="text-xs font-medium tabular-nums">{b.count.toLocaleString()}</span>
					<span
						class="w-full rounded-t-[3px] transition-opacity group-hover:opacity-80"
						style="height:{Math.max(3, (b.count / max) * 72)}px;background:{CERT_BUCKET_FILL[
							b.key
						] ?? 'var(--series)'}"
					></span>
				</span>
				<span class="text-center text-2xs leading-tight text-muted-foreground">{b.label}</span>
			</a>
		{/each}
	</div>
	{#snippet footer()}
		<span>{total.toLocaleString()} live web assets with a certificate</span>
	{/snippet}
</Cell>
