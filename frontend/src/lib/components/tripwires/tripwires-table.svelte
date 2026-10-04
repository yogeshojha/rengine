<script lang="ts">
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Switch } from '$lib/components/ui/switch';
	import Hint from '$lib/components/hint.svelte';
	import { HEAD_ROW, BODY_ROW } from '$lib/components/settings/columns';
	import { tripwiresStore } from '$lib/stores/tripwires.svelte';
	import {
		RECENT_DAYS,
		ActionKind,
		actionLabel,
		dimensionSpec,
		fireOnLabel,
		triggerLabel,
		TripwireTrigger
	} from '$lib/config/tripwires';
	import type { ScanAction, Tripwire } from '$lib/types/tripwire';
	import { relativeTime } from '$lib/utilities/dates';
	import QueryChip from './query-chip.svelte';
	import { TRIPWIRE_COL } from './columns';
	import { SHOWN_LABELS, scopeText } from './format';

	interface Props {
		tripwires: Tripwire[];
		onOpen: (tripwire: Tripwire) => void;
		onEdit: (tripwire: Tripwire) => void;
		onToggle: (tripwire: Tripwire, enabled: boolean) => void;
		onDelete: (tripwire: Tripwire) => void;
	}

	let { tripwires, onOpen, onEdit, onToggle, onDelete }: Props = $props();

	interface ThenChip {
		label: string;
		hint: string | null;
	}

	function thenChips(t: Tripwire): ThenChip[] {
		return t.actions.map((a) => {
			if (a.kind === ActionKind.Scan) {
				const stages = (a as ScanAction).stages.map((s) => tripwiresStore.stageTitle(s));
				return { label: actionLabel(a.kind), hint: stages.length ? stages.join(', ') : null };
			}
			return { label: actionLabel(a.kind), hint: null };
		});
	}
</script>

<div class="@container/tripwires w-full" role="table" aria-label="Tripwires">
	<div class={HEAD_ROW} role="row">
		<div class={TRIPWIRE_COL.tripwire} role="columnheader">Tripwire</div>
		<div class={TRIPWIRE_COL.fires} role="columnheader">Fires on</div>
		<div class={TRIPWIRE_COL.scope} role="columnheader">Scope</div>
		<div class={TRIPWIRE_COL.then} role="columnheader">Then</div>
		<div class={TRIPWIRE_COL.last} role="columnheader">Last fired</div>
		<div class={TRIPWIRE_COL.recent} role="columnheader">Fired, {RECENT_DAYS}d</div>
		<div class={TRIPWIRE_COL.enabled} role="columnheader"><span class="sr-only">Enabled</span></div>
		<div class={TRIPWIRE_COL.actions} role="columnheader"><span class="sr-only">Actions</span></div>
	</div>
	{#each tripwires as tripwire (tripwire.id)}
		{@const spec = dimensionSpec(tripwire.dimension)}
		<div class="{BODY_ROW} {tripwire.enabled ? '' : 'opacity-60'}" role="row">
			<div class="{TRIPWIRE_COL.tripwire} flex flex-col gap-1" role="cell">
				<button
					type="button"
					class="w-fit text-left text-sm leading-5 font-medium wrap-anywhere hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
					onclick={() => onOpen(tripwire)}
				>
					{tripwire.name}
				</button>
				<div class="flex min-w-0 items-center gap-1.5">
					<span class="shrink-0 text-2xs text-muted-foreground">{spec.label}</span>
					<QueryChip
						dimension={tripwire.dimension}
						query={tripwire.query}
						class="min-w-0 truncate"
					/>
				</div>
			</div>
			<div class={TRIPWIRE_COL.fires} role="cell">
				<div class="flex flex-col items-start gap-1">
					<Badge variant="outline" class="font-normal">{fireOnLabel(tripwire.fire_on)}</Badge>
					{#if tripwire.trigger === TripwireTrigger.ScanLive}
						<span class="text-2xs text-muted-foreground">{triggerLabel(tripwire.trigger)}</span>
					{/if}
				</div>
			</div>
			<div class="{TRIPWIRE_COL.scope} truncate text-sm" role="cell">
				<Hint
					text={tripwire.scope.labels.length > SHOWN_LABELS
						? tripwire.scope.labels.join(', ')
						: null}
				>
					{#snippet child(props)}
						<span {...props}>{scopeText(tripwire.scope, tripwire.scope.labels)}</span>
					{/snippet}
				</Hint>
			</div>
			<div class="{TRIPWIRE_COL.then} flex flex-wrap gap-1" role="cell">
				{#each thenChips(tripwire) as chip (chip.label)}
					<Hint text={chip.hint}>
						{#snippet child(props)}
							<Badge {...props} variant="secondary" class="font-normal">{chip.label}</Badge>
						{/snippet}
					</Hint>
				{/each}
				{#if tripwire.actions.length === 0}
					<span class="text-2xs text-muted-foreground">No action</span>
				{/if}
			</div>
			<div class="{TRIPWIRE_COL.last} text-sm text-muted-foreground" role="cell">
				{tripwire.last_fired_at ? relativeTime(tripwire.last_fired_at) : 'Not fired'}
			</div>
			<div class="{TRIPWIRE_COL.recent} text-sm tabular-nums" role="cell">
				{tripwire.recent_fired > 0 ? tripwire.recent_fired.toLocaleString() : ''}
			</div>
			<div class={TRIPWIRE_COL.enabled} role="cell">
				<Switch
					checked={tripwire.enabled}
					onCheckedChange={(v) => onToggle(tripwire, v)}
					aria-label={tripwire.enabled ? 'Pause tripwire' : 'Resume tripwire'}
				/>
			</div>
			<div class={TRIPWIRE_COL.actions} role="cell">
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon"
								class="size-7"
								aria-label="Tripwire actions"
							>
								<EllipsisIcon class="size-4" />
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content align="end">
						<DropdownMenu.Item onSelect={() => onOpen(tripwire)}>History</DropdownMenu.Item>
						<DropdownMenu.Item onSelect={() => onEdit(tripwire)}>Edit</DropdownMenu.Item>
						<DropdownMenu.Item onSelect={() => onToggle(tripwire, !tripwire.enabled)}>
							{tripwire.enabled ? 'Pause' : 'Resume'}
						</DropdownMenu.Item>
						<DropdownMenu.Separator />
						<DropdownMenu.Item variant="destructive" onSelect={() => onDelete(tripwire)}>
							Delete
						</DropdownMenu.Item>
					</DropdownMenu.Content>
				</DropdownMenu.Root>
			</div>
		</div>
	{/each}
</div>
