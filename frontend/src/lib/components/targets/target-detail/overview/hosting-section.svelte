<script lang="ts">
	import SectionHead from '../section-head.svelte';
	import HostingFlow from '$lib/components/scans/results/overview/hosting-flow.svelte';
	import type { HostingFlow as Flow } from '$lib/types/hosting-flow';

	interface Props {
		flow: Flow | null;
		onPick: (query: string) => void;
	}

	let { flow, onPick }: Props = $props();

	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;
</script>

{#if flow && flow.resolving > 0}
	<section class="flex flex-col gap-3 border-t py-5" style="--flow-halo: var(--background)">
		<SectionHead title="Hosting" count={plural(flow.networks, 'network', 'networks')}>
			<span class="tabular-nums">
				{flow.resolving.toLocaleString()} of {flow.hosts.toLocaleString()} resolve
			</span>
		</SectionHead>
		<HostingFlow {flow} {onPick} />
	</section>
{/if}
