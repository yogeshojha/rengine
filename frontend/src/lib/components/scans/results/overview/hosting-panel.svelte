<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import PanelHead from '$lib/components/panel-head.svelte';
	import HostingFlow from './hosting-flow.svelte';
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
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Hosting">
			<span class="tabular-nums">
				{flow.resolving.toLocaleString()} of {flow.hosts.toLocaleString()} resolve · {plural(
					flow.networks,
					'network',
					'networks'
				)}
			</span>
		</PanelHead>
		<div class="px-5 pt-4 pb-3">
			<HostingFlow {flow} {onPick} />
		</div>
	</Card.Root>
{/if}
