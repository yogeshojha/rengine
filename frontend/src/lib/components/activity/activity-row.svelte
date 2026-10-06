<script lang="ts">
	import RotateCw from '@lucide/svelte/icons/rotate-cw';
	import {
		ACTIVITY_EVENT,
		ACTIVITY_KINDS,
		type ActivityEvent,
		type ActivityTone
	} from '$lib/config/activity';
	import { ROUTES } from '$lib/config/routes';
	import type { ActivityLevel, ActivityLog } from '$lib/types/activity';
	import { activityLead } from '$lib/utilities/activity';
	import { relativeTime } from '$lib/utilities/dates';
	import { SCAN_STATUS_LABEL } from '$lib/utilities/scan-status';

	interface Props {
		row: ActivityLog;
		tick?: number;
		onNavigate?: () => void;
		onRescan?: (targetId: string) => void;
	}

	let { row, tick = 0, onNavigate, onRescan }: Props = $props();

	const TILE: Record<ActivityTone, string> = {
		neutral: 'bg-muted text-muted-foreground',
		warning: 'bg-warning/10 text-warning',
		error: 'bg-destructive/10 text-destructive'
	};
	const STATUS: Record<ActivityTone, string> = {
		neutral: 'text-muted-foreground',
		warning: 'font-medium text-warning',
		error: 'font-medium text-destructive'
	};
	const FACT: Record<ActivityLevel, string> = {
		error: 'font-medium text-sev-critical-ink',
		warning: 'font-medium text-sev-high-ink',
		info: 'text-foreground',
		success: ''
	};
	const RESCAN = new Set<ActivityEvent>([
		ACTIVITY_EVENT.SCAN_FAILED,
		ACTIVITY_EVENT.SCAN_CANCELLED
	]);

	let kind = $derived(ACTIVITY_KINDS[row.event_type]);
	let lead = $derived(activityLead(row));
	let mono = $derived(kind.byTarget && !!row.target_value);
	let status = $derived(kind.run ? SCAN_STATUS_LABEL[kind.run] : (kind.status ?? null));
	let fact = $derived(row.event_type === ACTIVITY_EVENT.SCAN_COMPLETED ? row.title : null);
	let rescan = $derived(RESCAN.has(row.event_type) && !!row.target_id && !!onRescan);
	let href = $derived.by(() => {
		if (row.scan_id) return ROUTES.scan(row.scan_id);
		if (row.event_type === ACTIVITY_EVENT.ISSUE_FAILED) return ROUTES.issueTrackers('issues');
		if (row.target_id) return ROUTES.target(row.target_id);
		if (row.event_type === ACTIVITY_EVENT.TARGET_BULK_IMPORTED) return ROUTES.targets;
		return null;
	});
	let time = $derived.by(() => {
		void tick;
		return relativeTime(row.timestamp);
	});
</script>

<div class="relative flex gap-3 px-3 py-2.5 transition-colors hover:bg-accent/40">
	<span class="mt-px flex size-7 shrink-0 items-center justify-center rounded-md {TILE[kind.tone]}">
		<kind.icon class="size-3.5" />
	</span>
	<div class="min-w-0 flex-1">
		<div class="flex h-5 items-center gap-2">
			{#if href}
				<a
					{href}
					onclick={() => onNavigate?.()}
					class="min-w-0 truncate font-medium outline-none after:absolute after:inset-0 after:rounded-none focus-visible:after:ring-2 focus-visible:after:ring-ring focus-visible:after:ring-inset {mono
						? 'font-mono text-xs'
						: 'text-sm'}"
				>
					{lead}
				</a>
			{:else}
				<span class="min-w-0 truncate font-medium {mono ? 'font-mono text-xs' : 'text-sm'}">
					{lead}
				</span>
			{/if}
			{#if status}
				<span class="shrink-0 text-xs {STATUS[kind.tone]}">{status}</span>
			{/if}
			<span class="ml-auto shrink-0 pl-2 font-mono text-2xs text-muted-foreground tabular-nums">
				{time}
			</span>
		</div>
		{#if fact || row.description}
			<p class="mt-0.5 line-clamp-2 text-xs leading-5 text-muted-foreground">
				{#if fact}
					<span class={FACT[row.level]}>{fact}</span>{#if row.description}<span aria-hidden="true">
							·
						</span>{/if}
				{/if}{row.description ?? ''}
			</p>
		{/if}
		{#if rescan && row.target_id}
			{@const targetId = row.target_id}
			<button
				type="button"
				onclick={() => onRescan?.(targetId)}
				class="relative z-[1] mt-1 inline-flex items-center gap-1 rounded-sm text-xs font-medium text-primary hover:text-primary/80 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
			>
				<RotateCw class="size-3" />
				Rescan
			</button>
		{/if}
	</div>
</div>
