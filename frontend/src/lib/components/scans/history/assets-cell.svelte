<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { ScanRead } from '$lib/types/scan';
	import { compactCount } from '$lib/utilities/numbers';

	const LEAD = [SurfaceDimension.WEB_ASSETS, SurfaceDimension.ENDPOINTS, SurfaceDimension.SERVICES];

	interface Props {
		scan: ScanRead;
	}

	let { scan }: Props = $props();

	let items = $derived(
		LEAD.map((key) => {
			const spec = SURFACE[key];
			const n = (scan[spec.countColumns[0]] as number) ?? 0;
			return { spec, n };
		})
	);
</script>

<div class="flex items-center gap-1">
	{#each items as { spec, n } (spec.key)}
		{@const Icon = spec.icon}
		<Hint text="{n.toLocaleString()} {n === 1 ? spec.noun : spec.nounPlural}">
			{#snippet child(props)}
				<a
					{...props}
					href={ROUTES.results(spec.tab, scan.id)}
					onclick={(e) => e.stopPropagation()}
					class="inline-flex h-6 items-center gap-1 rounded-md border border-border/70 px-1.5 font-mono text-xs tabular-nums transition-colors hover:border-foreground/30 hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {n
						? ''
						: 'text-muted-foreground/50'}"
					aria-label="{n} {spec.nounPlural}"
				>
					<Icon class="size-3 text-muted-foreground" />
					{compactCount(n)}
				</a>
			{/snippet}
		</Hint>
	{/each}
</div>
