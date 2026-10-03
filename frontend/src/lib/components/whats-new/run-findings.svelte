<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
	import { findingsFilter } from '$lib/components/scans/history/findings';
	import { NEW_FINDINGS_QUERY } from '$lib/config/whats-new';
	import { relativeTime } from '$lib/utilities/dates';
	import type { VulnerabilityRead } from '$lib/utilities/vulns';

	interface Props {
		projectId: string;
		scanId: string;
		count: number;
		onOpen: (vuln: VulnerabilityRead) => void;
	}

	let { projectId, scanId, count, onOpen }: Props = $props();

	const LIMIT = 50;
	let items = $state<VulnerabilityRead[] | null>(null);
	let total = $state(0);
	let failed = $state(false);

	$effect(() => {
		const scan = scanId;
		items = null;
		failed = false;
		vulnerabilitiesApi
			.search(projectId, scan, { ...findingsFilter([], LIMIT), q: NEW_FINDINGS_QUERY })
			.then((res) => {
				if (scan !== scanId) return;
				items = res.items;
				total = res.total;
			})
			.catch(() => (failed = true));
	});
</script>

{#if failed}
	<p class="text-xs text-muted-foreground">Findings not loaded.</p>
{:else if items === null}
	<div class="flex flex-col gap-1.5" aria-busy="true">
		{#each { length: Math.min(count, 4) } as _, i (i)}
			<Skeleton class="h-8 w-full rounded-md" />
		{/each}
	</div>
{:else}
	<ul class="divide-y divide-border/50 overflow-clip rounded-lg border bg-card">
		{#each items as v (v.id)}
			<li>
				<button
					type="button"
					class="flex w-full flex-col gap-0.5 px-3 py-2 text-left transition-colors hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none"
					onclick={() => onOpen(v)}
				>
					<span class="flex min-w-0 items-center gap-2">
						<SeverityMark severity={v.severity} class="hidden w-20 shrink-0 sm:flex" />
						<SeverityMark severity={v.severity} showLabel={false} class="shrink-0 sm:hidden" />
						<span class="min-w-0 flex-1 text-sm wrap-anywhere">{v.template_name}</span>
						{#if v.is_kev}<Badge variant="destructive">KEV</Badge>{/if}
					</span>
					<span class="flex min-w-0 items-baseline gap-2 pl-4 sm:pl-[5.5rem]">
						<span class="min-w-0 flex-1 font-mono text-xs text-muted-foreground wrap-anywhere">
							<span class="sm:hidden">{v.host || v.matched_at}</span>
							<span class="hidden sm:inline">{v.matched_at || v.host}</span>
						</span>
						<span class="shrink-0 text-2xs text-muted-foreground tabular-nums">
							{relativeTime(v.discovered_at)}
						</span>
					</span>
				</button>
			</li>
		{/each}
	</ul>
	{#if total > items.length}
		<span class="text-xs text-muted-foreground">
			{items.length} of {total.toLocaleString()} shown
		</span>
	{/if}
{/if}
