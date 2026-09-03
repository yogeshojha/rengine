<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ArrowDownRight from '@lucide/svelte/icons/arrow-down-right';
	import * as Card from '$lib/components/ui/card';
	import { Progress } from '$lib/components/ui/progress';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { elapsedSeconds, formatSeconds, isLiveStatus } from '$lib/utilities/scan-status';
	import { etaLabel, plannedStages, stageProgress } from '$lib/utilities/scan-progress';
	import { targetAssetNoun, TargetType } from '$lib/types/target';
	import type { ScanActivityRead, ScanRead } from '$lib/types/scan';
	import type { StageCatalogEntry } from '$lib/types/scan-engine';
	import type { LiveRun } from '$lib/stores/live-scans.svelte';

	interface Props {
		scan: ScanRead;
		previous: ScanRead | null;
		historyLoaded: boolean;
		resolved: number | null;
		run: LiveRun | undefined;
		catalog: StageCatalogEntry[];
		activities: ScanActivityRead[];
		previousDuration: number | null;
		now: number;
		onTab: (tab: string, filter?: string) => void;
	}

	let {
		scan,
		previous,
		historyLoaded,
		resolved,
		run,
		catalog,
		activities,
		previousDuration,
		now,
		onTab
	}: Props = $props();

	const fmtRun = (iso: string) =>
		new Date(iso).toLocaleString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit'
		});

	let type = $derived(scan.execution_config.target_type);
	let isDomain = $derived(type === TargetType.DOMAIN);
	let live = $derived(isLiveStatus(scan.status));
	let completed = $derived(scan.status === 'completed');
	let planned = $derived(plannedStages(scan, catalog));
	let progress = $derived(stageProgress(scan, run, planned));
	let doneCount = $derived(
		live
			? progress.done
			: planned.filter((s) => activities.some((a) => a.name === s.name && a.status === 'success'))
					.length
	);
	let elapsedSec = $derived(elapsedSeconds(scan, now));
	let eta = $derived(scan.status === 'running' ? etaLabel(previousDuration, elapsedSec) : null);
	let added = $derived(scan.new_subdomains ?? 0);
	let gone = $derived(scan.gone_subdomains ?? 0);
	let baseline = $derived(scan.is_first_scan === true || scan.prev_subdomains_found == null);
	let noun = (n: number) => targetAssetNoun(type, n);
	let nounPlural = $derived(targetAssetNoun(type));

	let headline = $derived.by(() => {
		switch (scan.status) {
			case 'pending':
				return 'Scan queued';
			case 'running':
				return 'Scan in progress';
			case 'failed':
				return 'Scan failed';
			case 'cancelled':
				return 'Scan cancelled';
			default:
				if (baseline) return 'Baseline established';
				if (added > 0) return `Attack surface grew by ${added.toLocaleString()} ${noun(added)}`;
				return gone > 0 ? 'No new assets discovered' : 'Attack surface unchanged';
		}
	});
	let subline = $derived.by(() => {
		switch (scan.status) {
			case 'pending':
				return 'Waiting for a worker to start this scan.';
			case 'running': {
				const parts = [run?.stage ? run.stage.title : progress.label];
				parts.push(`${progress.done} of ${progress.total} stages`);
				if (elapsedSec != null) parts.push(`${formatSeconds(elapsedSec)} elapsed`);
				if (eta) parts.push(eta);
				return parts.join(' · ');
			}
			case 'failed':
				return scan.error ?? 'A stage failed. See the pipeline log for details.';
			case 'cancelled':
				return `Stopped after ${doneCount} of ${planned.length} stages. Results are partial.`;
			default:
				if (baseline)
					return `Later scans of ${scan.execution_config.target_value} are compared with this one.`;
				if (!historyLoaded) return '';
				if (!previous) return 'Compared with the previous completed scan.';
				return `Compared with the ${previous.engine_name} scan on ${fmtRun(previous.started_at ?? previous.created_at)}.${gone > 0 ? ` ${gone.toLocaleString()} ${noun(gone)} no longer seen.` : ''}`;
		}
	});

	interface Kpi {
		key: string;
		label: string;
		value: number;
		tab: string;
		filter?: string;
		added?: number;
		gone?: number;
		diff?: number | null;
		hint?: string;
	}
	const diffVs = (now: number, before: number | undefined) =>
		before == null || now === before ? null : now - before;
	let kpis = $derived.by<Kpi[]>(() => {
		const cmp = completed && !baseline ? previous : null;
		const list: Kpi[] = [
			{
				key: 'subs',
				label: nounPlural.charAt(0).toUpperCase() + nounPlural.slice(1),
				value: scan.subdomains_found,
				tab: 'web-assets',
				added: completed && !baseline ? added : undefined,
				gone: completed && !baseline ? gone : undefined
			}
		];
		if (isDomain && resolved != null)
			list.push({
				key: 'resolved',
				label: 'Resolved',
				value: resolved,
				tab: 'web-assets',
				filter: 'is:resolved',
				hint:
					scan.subdomains_found > 0
						? `${Math.round((resolved / scan.subdomains_found) * 100)}% of ${nounPlural}`
						: undefined
			});
		list.push(
			{
				key: 'http',
				label: 'HTTP services',
				value: scan.http_assets_found,
				tab: 'web-assets',
				filter: 'is:web',
				diff: diffVs(scan.http_assets_found, cmp?.http_assets_found)
			},
			{
				key: 'ips',
				label: 'IP addresses',
				value: scan.ips_found,
				tab: 'ips',
				diff: diffVs(scan.ips_found, cmp?.ips_found)
			},
			{
				key: 'ports',
				label: 'Open ports',
				value: scan.open_ports_found,
				tab: 'ips',
				diff: diffVs(scan.open_ports_found, cmp?.open_ports_found)
			}
		);
		if (scan.vulnerabilities_found > 0)
			list.push({
				key: 'vulns',
				label: 'Vulnerabilities',
				value: scan.vulnerabilities_found,
				tab: 'web-assets'
			});
		if (scan.endpoints_found > 0)
			list.push({
				key: 'endpoints',
				label: 'Endpoints',
				value: scan.endpoints_found,
				tab: 'web-assets'
			});
		return list;
	});
</script>

<Card.Root class="gap-6">
	<Card.Header>
		<Card.Title class="flex items-center gap-2 text-base">
			{#if scan.status === 'running'}
				<Spinner class="size-4 text-info" />
			{/if}
			{headline}
		</Card.Title>
		{#if subline}
			<Card.Description>{subline}</Card.Description>
		{:else if !historyLoaded}
			<Skeleton class="h-4 w-64" />
		{/if}
		{#if scan.status === 'running' && progress.total > 0}
			<Progress
				value={progress.percent}
				class="mt-3 h-1.5"
				aria-label="{progress.percent}% of stages complete"
			/>
		{/if}
	</Card.Header>
	<Card.Content>
		<div class="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 lg:grid-cols-5">
			{#each kpis as k (k.key)}
				<button
					type="button"
					class="group flex cursor-pointer flex-col items-start gap-1 rounded-md text-left"
					onclick={() => onTab(k.tab, k.filter)}
				>
					<span class="text-2xl leading-none font-semibold">{k.value.toLocaleString()}</span>
					<span class="text-xs text-muted-foreground group-hover:text-foreground">{k.label}</span>
					{#if (k.added ?? 0) > 0 || (k.gone ?? 0) > 0}
						<span class="flex items-center gap-2 text-xs tabular-nums">
							{#if (k.added ?? 0) > 0}
								<span class="inline-flex items-center text-success">
									<ArrowUpRight class="size-3" />{k.added}
								</span>
							{/if}
							{#if (k.gone ?? 0) > 0}
								<span class="inline-flex items-center text-muted-foreground">
									<ArrowDownRight class="size-3" />{k.gone}
								</span>
							{/if}
						</span>
					{:else if k.diff != null}
						<span class="inline-flex items-center text-xs text-muted-foreground tabular-nums">
							{#if k.diff > 0}<ArrowUpRight class="size-3" />{:else}<ArrowDownRight
									class="size-3"
								/>{/if}
							{Math.abs(k.diff).toLocaleString()}
						</span>
					{:else if k.hint}
						<span class="text-xs text-muted-foreground tabular-nums">{k.hint}</span>
					{/if}
				</button>
			{/each}
		</div>
	</Card.Content>
</Card.Root>
