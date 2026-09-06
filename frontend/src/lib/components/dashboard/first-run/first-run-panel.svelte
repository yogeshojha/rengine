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
				sub="A scan discovers web assets, endpoints, services, addresses and vulnerabilities for one target."
			/>
		</div>
		<ReadinessStrip {readiness} />
	</Card.Root>
{/if}
