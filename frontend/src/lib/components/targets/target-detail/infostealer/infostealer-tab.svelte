<script lang="ts">
	import RecordShell from '../record-shell.svelte';
	import InfostealerStats from './infostealer-stats.svelte';
	import InfostealerHosts from './infostealer-hosts.svelte';
	import InfostealerBreakdown from './infostealer-breakdown.svelte';
	import { SOURCE_NAME, SOURCE_URL } from '$lib/config/infostealer';
	import type { InfostealerReport } from '$lib/types/infostealer';
	import { TaskStatus } from '$lib/types/task-status';
	import { externalHref } from '$lib/utilities/links';

	interface Props {
		domain: string;
		report: InfostealerReport | null;
		status: TaskStatus;
		error: string | null;
		loading: boolean;
		unloaded?: string | null;
		refreshing: boolean;
		onRefresh: () => void;
	}

	let {
		domain,
		report,
		status,
		error,
		loading,
		unloaded = null,
		refreshing,
		onRefresh
	}: Props = $props();
</script>

<RecordShell
	name="Infostealer"
	{status}
	{error}
	queriedAt={report?.checked_at}
	{refreshing}
	{loading}
	{unloaded}
	plain
	empty={!report || report.total === 0}
	emptyText="No infostealer infections reported for {report?.domain ?? domain}"
	{onRefresh}
>
	{#snippet bar()}
		<span class="text-sm">
			<span class="font-medium">Infostealer infections</span>
			<span class="text-muted-foreground">
				· {report?.domain ?? domain} ·
				<a
					href={externalHref(SOURCE_URL)}
					target="_blank"
					rel="noopener noreferrer"
					class="hover:text-foreground"
				>
					{SOURCE_NAME}
				</a>
			</span>
		</span>
	{/snippet}

	{#if report}
		<div class="flex flex-col gap-4">
			<InfostealerStats {report} />
			{#if report.hosts.length}
				<InfostealerHosts {report} />
			{/if}
			<InfostealerBreakdown {report} />
		</div>
	{/if}
</RecordShell>
