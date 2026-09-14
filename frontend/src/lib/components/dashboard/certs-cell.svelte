<script lang="ts">
	import Cell from './cell.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { CERT_BUCKET_FILL } from '$lib/config/dashboard';
	import type { DashboardCerts } from '$lib/types/dashboard';

	interface Props {
		certs: DashboardCerts;
		class?: string;
	}

	let { certs, class: className = '' }: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	let buckets = $derived(certs.buckets);
	let max = $derived(Math.max(1, ...buckets.map((b) => b.count)));
	let total = $derived(buckets.reduce((n, b) => n + b.count, 0));
	const link = (q: string) => ROUTES.surface(WEB.tab, { [WEB.queryParam]: q });
</script>

<Cell
	id="certs"
	title="Certificates"
	description="Live web assets by days to expiry"
	href={link(certs.expiring.query)}
	hrefLabel="cert:expiring"
	class={className}
>
	<div class="flex h-28 items-end gap-2">
		{#each buckets as b (b.key)}
			<a
				href={link(b.query)}
				class="group flex h-full flex-1 flex-col items-center justify-end gap-1"
				aria-label="{b.label}: {b.count}"
			>
				<span class="text-xs font-medium tabular-nums">{b.count.toLocaleString()}</span>
				<span
					class="w-full rounded-t-[3px] transition-opacity group-hover:opacity-80"
					style="height:{Math.max(3, (b.count / max) * 72)}px;background:{CERT_BUCKET_FILL[b.key] ??
						'var(--series)'}"
				></span>
				<span class="text-2xs whitespace-nowrap text-muted-foreground">{b.label}</span>
			</a>
		{/each}
	</div>
	{#snippet footer()}
		<span>{total.toLocaleString()} live web assets with a certificate</span>
	{/snippet}
</Cell>
