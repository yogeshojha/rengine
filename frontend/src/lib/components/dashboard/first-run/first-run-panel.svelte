<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import type { DashboardOverview, DashboardReadiness } from '$lib/types/dashboard';
	import Launcher from './launcher.svelte';
	import ReadinessStrip from './readiness-strip.svelte';
	import RunProgress from './run-progress.svelte';

	interface Props {
		overview: DashboardOverview | null;
		readiness: DashboardReadiness | null;
		now: number;
	}

	let { overview, readiness, now }: Props = $props();

	let live = $derived(liveScans.hasLive);
</script>

{#if live}
	<RunProgress {overview} {now} />
{:else}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<div class="px-5 py-5">
			<Launcher
				heading="No targets in this project"
				sub="Add a domain, IP address, IP range, URL or ASN."
			/>
		</div>
		<ReadinessStrip {readiness} />
	</Card.Root>
{/if}
