<script lang="ts">
	import Cell from '$lib/components/cell.svelte';
	import HostingBody, {
		coverage,
		networkNote
	} from '$lib/components/scans/results/overview/hosting-body.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { HOSTING_QUERIES } from '$lib/types/dashboard';
	import type { HostingComposition } from '$lib/types/hosting';

	interface Props {
		hosting: HostingComposition;
		scanId: string;
		onPick: (query: string) => void;
		class?: string;
	}

	let { hosting, scanId, onPick, class: className = '' }: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
</script>

<Cell
	skeleton="ranked"
	id="hosting"
	title="Hosting"
	description="By fronting and network"
	href={ROUTES.scanTab(scanId, WEB.tab, { [WEB.queryParam]: HOSTING_QUERIES.resolved })}
	hrefLabel={networkNote(hosting)}
	class={className}
>
	<HostingBody {hosting} {onPick} />
	{#snippet footer()}
		<span class="tabular-nums">{coverage(hosting)}</span>
	{/snippet}
</Cell>
