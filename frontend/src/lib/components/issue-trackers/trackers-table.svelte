<script lang="ts">
	import MoreVerticalIcon from '@lucide/svelte/icons/more-vertical';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import { CHECK_DOT, checkState } from '$lib/components/settings/status';
	import { TRACKERS_BY_KIND, trackerLabel } from '$lib/config/issue-trackers';
	import { relativeTime } from '$lib/utilities/dates';
	import type { IssueTracker } from '$lib/types/issue-tracker';
	import { BODY_ROW, HEAD_ROW, TRACKER_COL } from './columns';

	interface Props {
		trackers: IssueTracker[];
		canAdmin: boolean;
		testing: string | null;
		onEdit: (tracker: IssueTracker) => void;
		onTest: (tracker: IssueTracker) => void;
		onToggle: (tracker: IssueTracker) => void;
		onRemove: (tracker: IssueTracker) => void;
	}

	let { trackers, canAdmin, testing, onEdit, onTest, onToggle, onRemove }: Props = $props();

	const CHECK_LABEL = {
		ok: 'Connected',
		failed: 'Failed',
		untested: 'Not tested',
		off: 'Disabled'
	} as const;
</script>

<div class="@container/trackers w-full" role="table" aria-label="Issue trackers">
	<div class={HEAD_ROW} role="row">
		<div class={TRACKER_COL.tracker}>Tracker</div>
		<div class={TRACKER_COL.destination}>Default destination</div>
		<div class={TRACKER_COL.issues}>Issues</div>
		<div class={TRACKER_COL.check}>Connection</div>
		<div class={TRACKER_COL.actions}></div>
	</div>
	{#each trackers as tracker (tracker.id)}
		{@const spec = TRACKERS_BY_KIND[tracker.kind]}
		{@const check = checkState(tracker.is_active, tracker.last_test_ok)}
		<div class="{BODY_ROW} {tracker.is_active ? '' : 'text-muted-foreground'}" role="row">
			<div class={TRACKER_COL.tracker}>
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
			<div class="{TRACKER_COL.destination} text-sm leading-5 wrap-anywhere">
				{#if tracker.destination}
					<span class="font-mono">{tracker.destination}</span>
					{#if spec?.hasIssueType && tracker.issue_type}
						<div class="text-2xs text-muted-foreground">{tracker.issue_type}</div>
					{/if}
				{:else}
					<span class="text-muted-foreground">None</span>
				{/if}
			</div>
			<div class="{TRACKER_COL.issues} text-sm leading-5 tabular-nums">
				{tracker.issues_filed.toLocaleString()}
				{#if tracker.issues_failed}
					<div class="text-2xs text-destructive">{tracker.issues_failed} not filed</div>
				{/if}
			</div>
			<div class="{TRACKER_COL.check} text-sm leading-5">
				<Hint text={check === 'failed' ? (tracker.last_test_message ?? '') : ''}>
					{#snippet child(props)}
						<span {...props} class="inline-flex items-center gap-2">
							<span class="flex h-5 items-center">
								<span class="size-2 rounded-full {CHECK_DOT[check]}" aria-hidden="true"></span>
							</span>
							{CHECK_LABEL[check]}
						</span>
					{/snippet}
				</Hint>
				{#if tracker.last_test_at}
					<div class="text-2xs text-muted-foreground">{relativeTime(tracker.last_test_at)}</div>
				{/if}
			</div>
			<div class={TRACKER_COL.actions}>
				{#if canAdmin}
					<DropdownMenu.Root>
						<DropdownMenu.Trigger>
							{#snippet child({ props })}
								<Button {...props} variant="ghost" size="icon" class="size-7">
									<MoreVerticalIcon class="size-4" />
									<span class="sr-only">Tracker actions</span>
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
