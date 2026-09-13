<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import PanelHead from '$lib/components/panel-head.svelte';
	import HostingBody, { coverage, networkNote } from './hosting-body.svelte';
	import type { HostingComposition } from '$lib/types/hosting';

	interface Props {
		hosting: HostingComposition | null;
		onPick: (query: string) => void;
	}

	let { hosting, onPick }: Props = $props();
</script>

{#if hosting && hosting.resolving > 0}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead title="Hosting">
			<span class="tabular-nums">{coverage(hosting)} · {networkNote(hosting)}</span>
		</PanelHead>
		<HostingBody {hosting} {onPick} class="p-5" />
	</Card.Root>
{/if}
