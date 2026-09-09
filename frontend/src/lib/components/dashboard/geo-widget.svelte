<script lang="ts">
	import { goto } from '$app/navigation';
	import Widget from './widget.svelte';
	import Globe from '$lib/components/scans/results/overview/globe.svelte';
	import CountryFlag from '$lib/components/scans/results/country-flag.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { countryName } from '$lib/config/country-geo';
	import type { Facet } from '$lib/utilities/scan-insights';

	interface Props {
		countries: Facet[] | null;
		loading?: boolean;
		class?: string;
	}

	let { countries, loading = false, class: className = '' }: Props = $props();

	const TOP = 5;
	const SPEC = SURFACE[SurfaceDimension.IPS];
	const link = (code: string) =>
		ROUTES.surface(SPEC.tab, { [SPEC.queryParam]: `country:${code.toUpperCase()}` });

	let entries = $derived((countries ?? []).map((f) => ({ code: f.value, count: f.count })));
	let total = $derived(entries.reduce((n, e) => n + e.count, 0));
	let top = $derived(entries.slice(0, TOP));
	let rest = $derived(entries.length - top.length);
	let restCount = $derived(entries.slice(TOP).reduce((n, e) => n + e.count, 0));
	let max = $derived(Math.max(1, ...top.map((e) => e.count)));
	let active = $state<string | null>(null);
</script>

<Widget
	title="Geography"
	description="Where the addresses answer from"
	href={ROUTES.surface(SPEC.tab)}
	hrefLabel="IP addresses"
	loading={loading && !countries}
	class={className}
>
	<div class="flex flex-col items-center gap-3 px-5 py-4">
		<Globe
			{entries}
			size={176}
			class="w-44"
			activeCode={active}
			onPick={(code) => goto(link(code))}
			onHover={(code) => (active = code)}
		/>
		<ul class="flex w-full flex-col gap-1.5">
			{#each top as e (e.code)}
				<li>
					<a
						href={link(e.code)}
						class="group flex flex-col gap-1 rounded-sm"
						onmouseenter={() => (active = e.code)}
						onmouseleave={() => (active = null)}
					>
						<span class="flex items-center gap-2 text-sm">
							<CountryFlag code={e.code} showCode={false} class="shrink-0" />
							<span class="min-w-0 flex-1 truncate group-hover:text-foreground">
								{countryName(e.code)}
							</span>
							<span class="font-medium tabular-nums">{e.count.toLocaleString()}</span>
							<span class="w-9 text-right text-[11px] text-muted-foreground tabular-nums">
								{total ? Math.round((e.count / total) * 100) : 0}%
							</span>
						</span>
						<span class="h-1 w-full overflow-hidden rounded-full bg-muted">
							<span
								class="block h-full rounded-full bg-chart-1 transition-opacity {active &&
								active !== e.code
									? 'opacity-40'
									: ''}"
								style="width:{Math.max(1.5, (e.count / max) * 100)}%"
							></span>
						</span>
					</a>
				</li>
			{/each}
		</ul>
	</div>
	{#snippet footer()}
		{#if rest > 0}
			{restCount.toLocaleString()} more {restCount === 1 ? 'address' : 'addresses'} in {rest} other
			{rest === 1 ? 'country' : 'countries'}
		{:else}
			{total.toLocaleString()} {total === 1 ? 'address' : 'addresses'} with a resolved country
		{/if}
	{/snippet}
</Widget>
