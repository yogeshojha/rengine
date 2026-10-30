<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { ScanRead } from '$lib/types/scan';
	import { compactCount } from '$lib/utilities/numbers';

	const LEAD = [SurfaceDimension.WEB_ASSETS, SurfaceDimension.ENDPOINTS, SurfaceDimension.SERVICES];
	const OK_QUERY = 'status:2xx';

	interface Props {
		scan: ScanRead;
	}

	let { scan }: Props = $props();

	let ok = $derived(scan.web_assets_ok ?? null);
	let items = $derived(
		LEAD.map((key) => {
			const spec = SURFACE[key];
			const n = (scan[spec.countColumns[0]] as number) ?? 0;
			return { spec, n };
		})
	);

	const SEGMENT =
		'inline-flex h-full items-center gap-1 px-1.5 transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none';
</script>

<div class="flex items-center gap-1">
	{#each items as { spec, n } (spec.key)}
		{@const Icon = spec.icon}
		{@const live = spec.key === SurfaceDimension.WEB_ASSETS && ok !== null && n > 0}
		<span
			class="inline-flex h-6 items-stretch overflow-hidden rounded-md border font-mono text-xs tabular-nums {live
				? 'border-success/30'
				: 'border-border/70 hover:border-foreground/30'}"
		>
			<Hint text="{n.toLocaleString()} {n === 1 ? spec.noun : spec.nounPlural}">
				{#snippet child(props)}
					<a
						{...props}
						href={ROUTES.results(spec.tab, scan.id)}
						onclick={(e) => e.stopPropagation()}
						class="{SEGMENT} hover:bg-muted {n ? '' : 'text-muted-foreground/50'}"
						aria-label="{n} {spec.nounPlural}"
					>
						<Icon class="size-3 text-muted-foreground" />
						{compactCount(n)}
					</a>
				{/snippet}
			</Hint>
			{#if live && ok !== null}
				<Hint text="{ok.toLocaleString()} of {n.toLocaleString()} {spec.nounPlural} returned 2xx">
					{#snippet child(props)}
						<a
							{...props}
							href={ROUTES.results(spec.tab, scan.id, { [spec.queryParam]: OK_QUERY })}
							onclick={(e) => e.stopPropagation()}
							class="{SEGMENT} border-l border-success/30 bg-success/10 text-success hover:bg-success/20 {ok
								? ''
								: 'opacity-60'}"
							aria-label="{ok} {spec.nounPlural} returned 2xx"
						>
							<span class="size-1.5 rounded-full bg-success"></span>
							{compactCount(ok)}
						</a>
					{/snippet}
				</Hint>
			{/if}
		</span>
	{/each}
</div>
