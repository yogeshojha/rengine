<script lang="ts">
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import TicketChip from './ticket-chip.svelte';
	import { FilingState } from '$lib/config/issue-trackers';
	import { relativeTime } from '$lib/utilities/dates';
	import { externalHref } from '$lib/utilities/links';
	import { ROUTES } from '$lib/config/routes';
	import type { TrackedIssue } from '$lib/types/issue-tracker';
	import { HEAD_ROW } from '$lib/components/settings/columns';
	import { BODY_ROW, ISSUE_COL } from './columns';

	interface Props {
		issues: TrackedIssue[];
		onRetry: (issue: TrackedIssue) => void;
		onRefresh: (issue: TrackedIssue) => void;
		onUnlink: (issue: TrackedIssue) => void;
	}

	let { issues, onRetry, onRefresh, onUnlink }: Props = $props();
</script>

<div class="@container/issues w-full" role="table" aria-label="Filed issues">
	<div class={HEAD_ROW} role="row">
		<div class={ISSUE_COL.issue}>Issue</div>
		<div class={ISSUE_COL.title}>Title</div>
		<div class={ISSUE_COL.target}>Target</div>
		<div class={ISSUE_COL.findings}>Findings</div>
		<div class={ISSUE_COL.filed}>Filed</div>
		<div class={ISSUE_COL.actions}></div>
	</div>
	{#each issues as issue (issue.id)}
		<div class={BODY_ROW} role="row">
			<div class={ISSUE_COL.issue}>
				<TicketChip
					state={issue.state}
					externalKey={issue.external_key}
					url={issue.url}
					remoteStatus={issue.remote_status}
					remoteCategory={issue.remote_category}
					error={issue.error}
					trackerName={issue.tracker_name}
				/>
			</div>
			<div class={ISSUE_COL.title}>
				<div class="text-sm leading-5 wrap-anywhere">{issue.title}</div>
				<div class="flex flex-wrap items-center gap-2 text-2xs text-muted-foreground">
					<SeverityMark severity={issue.severity} />
					<span>{issue.tracker_name}</span>
					<span class="font-mono">{issue.destination}</span>
				</div>
			</div>
			<div class="{ISSUE_COL.target} text-sm leading-5 wrap-anywhere">
				{#if issue.target_value}
					<a href={ROUTES.target(issue.target_id)} class="font-mono hover:text-primary">
						{issue.target_value}
					</a>
				{/if}
			</div>
			<div class="{ISSUE_COL.findings} text-sm leading-5 tabular-nums">
				{issue.findings.toLocaleString()}
				{#if issue.present < issue.findings}
					<div class="text-2xs text-muted-foreground">
						{(issue.findings - issue.present).toLocaleString()} not observed
					</div>
				{/if}
			</div>
			<div class="{ISSUE_COL.filed} text-sm leading-5">
				{issue.filed_at ? relativeTime(issue.filed_at) : ''}
			</div>
			<div class={ISSUE_COL.actions}>
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon"
								class="size-7"
								aria-label="Issue actions"
							>
								<EllipsisIcon class="size-4" />
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content align="end" class="w-48">
						{#if issue.url}
							<DropdownMenu.Item>
								{#snippet child({ props })}
									<a
										{...props}
										href={externalHref(issue.url)}
										target="_blank"
										rel="noopener noreferrer"
									>
										Open in {issue.tracker_name}
									</a>
								{/snippet}
							</DropdownMenu.Item>
						{/if}
						{#if issue.state === FilingState.FAILED}
							<DropdownMenu.Item onSelect={() => onRetry(issue)}>Retry filing</DropdownMenu.Item>
						{/if}
						{#if issue.state === FilingState.FILED}
							<DropdownMenu.Item onSelect={() => onRefresh(issue)}>Refresh status</DropdownMenu.Item
							>
						{/if}
						{#if issue.url || issue.state === FilingState.FAILED || issue.state === FilingState.FILED}
							<DropdownMenu.Separator />
						{/if}
						<DropdownMenu.Item variant="destructive" onSelect={() => onUnlink(issue)}>
							Unlink
						</DropdownMenu.Item>
					</DropdownMenu.Content>
				</DropdownMenu.Root>
			</div>
		</div>
	{/each}
</div>
