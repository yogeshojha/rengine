<script lang="ts">
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import CheckStatus from '$lib/components/settings/check-status.svelte';
	import { checkState } from '$lib/components/settings/status';
	import { TRACKERS_BY_KIND, trackerLabel } from '$lib/config/issue-trackers';
	import { relativeTime } from '$lib/utilities/dates';
	import { FilingState } from '$lib/config/issue-trackers';
	import type { IssueTracker, TrackedIssue } from '$lib/types/issue-tracker';
	import { HEAD_ROW } from '$lib/components/settings/columns';
	import { BODY_ROW, TRACKER_COL } from './columns';

	interface Props {
		trackers: IssueTracker[];
		issues: TrackedIssue[];
		capped: boolean;
		canAdmin: boolean;
		testing: string | null;
		onEdit: (tracker: IssueTracker) => void;
		onTest: (tracker: IssueTracker) => void;
		onToggle: (tracker: IssueTracker) => void;
		onRemove: (tracker: IssueTracker) => void;
		onOpenIssues: (tracker: IssueTracker) => void;
	}

	let {
		trackers,
		issues,
		capped,
		canAdmin,
		testing,
		onEdit,
		onTest,
		onToggle,
		onRemove,
		onOpenIssues
	}: Props = $props();

	const tally = $derived.by(() => {
		const out: Record<string, { total: number; failed: number }> = {};
		for (const issue of issues) {
			const row = (out[issue.tracker_id] ??= { total: 0, failed: 0 });
			row.total += 1;
			if (issue.state === FilingState.FAILED) row.failed += 1;
		}
		return out;
	});

	const CHECK_LABEL = {
		ok: 'Connected',
		failed: 'Failed',
		untested: 'Not tested',
		off: 'Disabled'
	} as const;
</script>

<div class="@container/trackers w-full" role="table" aria-label="Issue trackers">
	<div class={HEAD_ROW} role="row">
		<div class={TRACKER_COL.tracker} role="columnheader">Tracker</div>
		<div class={TRACKER_COL.destination} role="columnheader">Default destination</div>
		<div class={TRACKER_COL.issues} role="columnheader">Issues</div>
		<div class={TRACKER_COL.check} role="columnheader">Connection</div>
		<div class={TRACKER_COL.actions} role="columnheader"><span class="sr-only">Actions</span></div>
	</div>
	{#each trackers as tracker (tracker.id)}
		{@const spec = TRACKERS_BY_KIND[tracker.kind]}
		{@const check = checkState(tracker.is_active, tracker.last_test_ok)}
		{@const count = tally[tracker.id] ?? { total: 0, failed: 0 }}
		<div class="{BODY_ROW} {tracker.is_active ? '' : 'text-muted-foreground'}" role="row">
			<div class={TRACKER_COL.tracker} role="cell">
				{#if canAdmin}
					<button
						type="button"
						class="text-left text-sm leading-5 font-medium wrap-anywhere hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
						onclick={() => onEdit(tracker)}
					>
						{tracker.name}
					</button>
				{:else}
					<div class="text-sm leading-5 font-medium wrap-anywhere">{tracker.name}</div>
				{/if}
				<div class="text-2xs text-muted-foreground wrap-anywhere">
					{trackerLabel(tracker.kind)} · <span class="font-mono">{tracker.url}</span>
				</div>
			</div>
			<div class="{TRACKER_COL.destination} text-sm leading-5 wrap-anywhere" role="cell">
				{#if tracker.destination}
					<span class="font-mono">{tracker.destination}</span>
					{#if spec?.hasIssueType && tracker.issue_type}
						<div class="text-2xs text-muted-foreground">{tracker.issue_type}</div>
					{/if}
				{:else}
					<span class="text-muted-foreground">None</span>
				{/if}
			</div>
			<div class="{TRACKER_COL.issues} text-sm leading-5 tabular-nums" role="cell">
				{#if count.total}
					<button
						type="button"
						class="hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
						onclick={() => onOpenIssues(tracker)}
					>
						{count.total.toLocaleString()}{capped ? '+' : ''}
					</button>
				{:else}
					<span class="text-muted-foreground">0{capped ? '+' : ''}</span>
				{/if}
				{#if count.failed}
					<div class="text-2xs text-destructive">{count.failed.toLocaleString()} not filed</div>
				{/if}
			</div>
			<div class="{TRACKER_COL.check} text-sm leading-5" role="cell">
				<CheckStatus
					{check}
					label={CHECK_LABEL[check]}
					message={check === 'failed' ? tracker.last_test_message : null}
				/>
				{#if tracker.last_test_at}
					<div class="text-2xs text-muted-foreground">{relativeTime(tracker.last_test_at)}</div>
				{/if}
			</div>
			<div class={TRACKER_COL.actions} role="cell">
				{#if canAdmin}
					<DropdownMenu.Root>
						<DropdownMenu.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="ghost"
									size="icon"
									class="size-7"
									aria-label="Tracker actions"
								>
									<EllipsisIcon class="size-4" />
								</Button>
							{/snippet}
						</DropdownMenu.Trigger>
						<DropdownMenu.Content align="end">
							<DropdownMenu.Item disabled={testing === tracker.id} onSelect={() => onTest(tracker)}>
								Test connection
							</DropdownMenu.Item>
							<DropdownMenu.Item onSelect={() => onEdit(tracker)}>Edit</DropdownMenu.Item>
							<DropdownMenu.Item onSelect={() => onToggle(tracker)}>
								{tracker.is_active ? 'Disable' : 'Enable'}
							</DropdownMenu.Item>
							<DropdownMenu.Separator />
							<DropdownMenu.Item variant="destructive" onSelect={() => onRemove(tracker)}>
								Remove
							</DropdownMenu.Item>
						</DropdownMenu.Content>
					</DropdownMenu.Root>
				{/if}
			</div>
		</div>
	{/each}
</div>
