<script lang="ts">
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import type { IssueTracker, TrackerRoute } from '$lib/types/issue-tracker';
	import { HEAD_ROW } from '$lib/components/settings/columns';
	import { BODY_ROW, ROUTE_COL } from './columns';

	interface Props {
		routes: TrackerRoute[];
		trackers: IssueTracker[];
		projectName: string;
		canAdmin: boolean;
		onEdit: (route: TrackerRoute) => void;
		onRemove: (route: TrackerRoute) => void;
	}

	let { routes, trackers, projectName, canAdmin, onEdit, onRemove }: Props = $props();

	const names = $derived(new Map(trackers.map((t) => [t.id, t])));
</script>

<div class="@container/routes w-full" role="table" aria-label="Routes">
	<div class={HEAD_ROW} role="row">
		<div class={ROUTE_COL.scope} role="columnheader">Applies to</div>
		<div class={ROUTE_COL.tracker} role="columnheader">Tracker</div>
		<div class={ROUTE_COL.destination} role="columnheader">Destination</div>
		<div class={ROUTE_COL.type} role="columnheader">Issue type</div>
		<div class={ROUTE_COL.actions} role="columnheader"><span class="sr-only">Actions</span></div>
	</div>
	{#each routes as route (route.id)}
		{@const tracker = names.get(route.tracker_id)}
		<div class={BODY_ROW} role="row">
			<div class="{ROUTE_COL.scope} text-sm leading-5 wrap-anywhere" role="cell">
				{#if route.target_id}
					<span class="font-mono">{route.target_value}</span>
				{:else}
					Every target in {projectName}
				{/if}
			</div>
			<div class="{ROUTE_COL.tracker} text-sm leading-5 wrap-anywhere" role="cell">
				{tracker?.name ?? ''}
				{#if tracker && !tracker.is_active}
					<div class="text-2xs text-muted-foreground">Disabled</div>
				{/if}
			</div>
			<div class="{ROUTE_COL.destination} font-mono text-sm leading-5 wrap-anywhere" role="cell">
				{route.destination}
			</div>
			<div class="{ROUTE_COL.type} text-sm leading-5" role="cell">
				{route.issue_type ?? ''}
			</div>
			<div class={ROUTE_COL.actions} role="cell">
				{#if canAdmin}
					<DropdownMenu.Root>
						<DropdownMenu.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="ghost"
									size="icon"
									class="size-7"
									aria-label="Route actions"
								>
									<EllipsisIcon class="size-4" />
								</Button>
							{/snippet}
						</DropdownMenu.Trigger>
						<DropdownMenu.Content align="end">
							<DropdownMenu.Item onSelect={() => onEdit(route)}>Edit</DropdownMenu.Item>
							<DropdownMenu.Separator />
							<DropdownMenu.Item variant="destructive" onSelect={() => onRemove(route)}>
								Remove
							</DropdownMenu.Item>
						</DropdownMenu.Content>
					</DropdownMenu.Root>
				{/if}
			</div>
		</div>
	{/each}
</div>
