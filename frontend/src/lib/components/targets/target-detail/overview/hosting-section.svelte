<script lang="ts">
	import SectionHead from '$lib/components/section-head.svelte';
	import HostingBody, {
		coverage,
		networkNote
	} from '$lib/components/scans/results/overview/hosting-body.svelte';
	import type { HostingComposition } from '$lib/types/hosting';

	interface Props {
		hosting: HostingComposition | null;
		onPick: (query: string) => void;
	}

	let { hosting, onPick }: Props = $props();
</script>

{#if hosting && hosting.resolving > 0}
	<section class="flex flex-col gap-3 border-t py-5">
		<SectionHead title="Hosting" count={networkNote(hosting)}>
			<span class="tabular-nums">{coverage(hosting)}</span>
		</SectionHead>
		<HostingBody {hosting} {onPick} />
	</section>
{/if}
