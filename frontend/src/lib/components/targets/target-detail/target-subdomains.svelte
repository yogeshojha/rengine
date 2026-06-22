<script lang="ts">
	import { untrack } from 'svelte';
	import { Network } from 'lucide-svelte';
	import { subdomainsApi } from '$lib/api/subdomains';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import SubdomainTable from '$lib/components/scans/subdomain-table.svelte';
	import ScanTabEmpty from '$lib/components/targets/target-detail/summary/scan-tab-empty.svelte';
	import type { TargetSubdomainRead } from '$lib/types/subdomain';

	interface Props {
		targetId: string;
		onScan?: () => void;
	}
	let { targetId, onScan }: Props = $props();

	let rows = $state<TargetSubdomainRead[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	let tableRows = $derived(
		rows.map((r) => ({
			name: r.name,
			sources: r.sources,
			resolved_ips: r.resolved_ips,
			is_active: r.is_active,
			is_wildcard: r.is_wildcard,
			is_excluded: r.is_excluded,
			last_seen: r.last_seen,
			scan_count: r.scan_count
		}))
	);
	let activeCount = $derived(rows.filter((r) => r.is_active).length);

	async function load() {
		const project = projectsStore.activeProject;
		if (!project) return;
		loading = true;
		error = null;
		try {
			rows = await subdomainsApi.rollup(project.id, targetId, { limit: 1000 });
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load subdomains';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		const project = projectsStore.activeProject;
		const tid = targetId;
		if (project && tid) untrack(() => load());
	});
</script>

{#if loading && rows.length === 0}
	<div class="space-y-2">
		{#each Array(4) as _, i (i)}
			<Skeleton class="h-12 w-full" />
		{/each}
	</div>
{:else if error}
	<p class="text-sm text-destructive">{error}</p>
{:else if rows.length === 0}
	<ScanTabEmpty
		icon={Network}
		title="No subdomains discovered yet"
		description="Run a reconnaissance scan to enumerate subdomains for this target."
		{onScan}
	/>
{:else}
	<div class="space-y-3">
		<p class="text-sm text-muted-foreground">
			{rows.length} subdomains · {activeCount} live · current attack surface across all scans
		</p>
		<SubdomainTable rows={tableRows} showScans />
	</div>
{/if}
