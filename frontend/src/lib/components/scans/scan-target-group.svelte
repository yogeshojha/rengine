<script lang="ts">
	import { ChevronRight, Loader } from 'lucide-svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CopyButton from '@/components/copy-button.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { SCAN_STATUS_LABEL, scanStatusVariant, scanStatusIcon } from '$lib/utilities/scan-status';
	import { getTargetTypeColor, formatTargetType, type TargetType } from '$lib/types/target';
	import type { ScanRead, ScanTargetGroup } from '$lib/types/scan';
	import ScanListItem from './scan-list-item.svelte';
	import ScanTrendSparkline from './scan-trend-sparkline.svelte';

	const STALE_MS = 30 * 24 * 60 * 60 * 1000;

	interface Props {
		group: ScanTargetGroup;
		now: number;
		loadScans: (targetId: string) => Promise<ScanRead[]>;
		onRescan: (scan: ScanRead) => void;
		onCancel: (scan: ScanRead) => void;
		onDelete: (scan: ScanRead) => void;
	}

	let { group, now, loadScans, onRescan, onCancel, onDelete }: Props = $props();

	let expanded = $state(false);
	let loading = $state(false);
	let loaded = $state(false);
	let scans = $state<ScanRead[]>([]);

	let StatusIcon = $derived(scanStatusIcon(group.last_status));
	let stale = $derived(
		group.running === 0 && now - new Date(group.last_scan_at).getTime() > STALE_MS
	);

	async function toggle() {
		expanded = !expanded;
		if (expanded && !loaded && !loading) {
			loading = true;
			try {
				scans = await loadScans(group.target_id);
				loaded = true;
			} catch {
				scans = [];
			} finally {
				loading = false;
			}
		}
	}
</script>

<div>
	<button
		type="button"
		class="group flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-muted/30"
		onclick={toggle}
		aria-expanded={expanded}
	>
		<ChevronRight
			class="h-4 w-4 shrink-0 text-muted-foreground transition-transform {expanded
				? 'rotate-90'
				: ''}"
		/>

		<div class="flex min-w-0 flex-1 items-center gap-2">
			<span class="truncate font-mono text-sm font-medium">{group.target_value}</span>
			<Badge
				variant="outline"
				class="shrink-0 rounded px-1.5 py-0.5 text-[10px] {getTargetTypeColor(
					group.target_type as TargetType
				)}"
			>
				{formatTargetType(group.target_type as TargetType)}
			</Badge>
			<CopyButton
				value={group.target_value}
				class="shrink-0 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100"
			/>
		</div>

		<div class="hidden shrink-0 lg:block">
			<ScanTrendSparkline values={group.trend} />
		</div>

		{#if group.running > 0}
			<Badge variant="secondary" class="shrink-0 gap-1 font-normal">
				<Loader class="h-3 w-3 animate-spin" />
				{group.running} running
			</Badge>
		{:else if stale}
			<Badge
				variant="outline"
				class="shrink-0 gap-1 border-amber-500/30 font-normal text-amber-600 dark:text-amber-500"
			>
				Stale
			</Badge>
		{/if}

		<Badge
			variant={scanStatusVariant(group.last_status)}
			class="hidden shrink-0 gap-1 font-normal sm:inline-flex"
		>
			<StatusIcon class="h-3 w-3 {group.last_status === 'running' ? 'animate-spin' : ''}" />
			{SCAN_STATUS_LABEL[group.last_status]}
		</Badge>

		<span
			class="hidden w-16 shrink-0 text-right text-xs text-muted-foreground tabular-nums sm:block"
		>
			{group.scan_count} scan{group.scan_count !== 1 ? 's' : ''}
		</span>

		<span class="w-[110px] shrink-0 text-right text-xs text-muted-foreground">
			{relativeTime(group.last_scan_at)}
		</span>
	</button>

	{#if expanded}
		<div class="border-t border-border/50 bg-muted/20 pl-6">
			{#if loading}
				<div class="space-y-2 px-4 py-3">
					{#each Array(2) as _, i (i)}
						<Skeleton class="h-8 w-full" />
					{/each}
				</div>
			{:else if scans.length === 0}
				<div class="px-4 py-4 text-xs text-muted-foreground">
					No scans match the current filters.
				</div>
			{:else}
				<div class="divide-y divide-border/50">
					{#each scans as scan (scan.id)}
						<ScanListItem
							{scan}
							targetId={group.target_id}
							{now}
							{onRescan}
							{onCancel}
							{onDelete}
						/>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>
