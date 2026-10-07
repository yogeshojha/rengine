<script lang="ts">
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Select from '$lib/components/ui/select';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';
	import { Button } from '$lib/components/ui/button';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import DestinationPicker from './destination-picker.svelte';
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { pluralLabel } from '$lib/utilities/strings';
	import { issueTrackersApi } from '$lib/api/issue-trackers';
	import { targetsApi } from '$lib/api/targets';
	import { issueTrackers } from '$lib/stores/issue-trackers.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { SELECT_NONE } from '$lib/constants';
	import { TRACKERS_BY_KIND } from '$lib/config/issue-trackers';
	import type { TrackerRoute } from '$lib/types/issue-tracker';

	interface Props {
		open: boolean;
		editing: TrackerRoute | null;
	}

	let { open = $bindable(), editing }: Props = $props();

	const SEARCH_LIMIT = 20;
	const SEARCH_DELAY_MS = 250;

	let targetId = $state<string>(SELECT_NONE);
	let targetValue = $state('');
	let trackerId = $state('');
	let destination = $state('');
	let issueType = $state('');
	let saving = $state(false);
	let pickerOpen = $state(false);
	let search = $state('');
	let found = $state<{ id: string; value: string }[]>([]);
	let initial = $state('');
	let searchReq = 0;

	const project = $derived(projectsStore.activeProject);
	const trackers = $derived(issueTrackers.trackers);
	const tracker = $derived(trackers.find((t) => t.id === trackerId) ?? null);
	const spec = $derived(tracker ? TRACKERS_BY_KIND[tracker.kind] : null);
	const dirty = $derived(snapshot() !== initial);
	const guard = new DiscardGuard(
		() => dirty,
		() => (open = false)
	);

	function snapshot(): string {
		return JSON.stringify([targetId, trackerId, destination.trim(), issueType.trim()]);
	}

	$effect(() => {
		if (!open) return;
		const row = editing;
		untrack(() => {
			const first = issueTrackers.active[0];
			targetId = row?.target_id ?? SELECT_NONE;
			targetValue = row?.target_value ?? '';
			trackerId = row?.tracker_id ?? first?.id ?? '';
			destination = row?.destination ?? first?.destination ?? '';
			issueType = row?.issue_type ?? '';
			initial = snapshot();
		});
	});

	$effect(() => {
		if (!pickerOpen || !project) return;
		const q = search;
		const slug = project.slug;
		const my = ++searchReq;
		const timer = setTimeout(async () => {
			try {
				const page = await targetsApi.list({ project_slug: slug, search: q, size: SEARCH_LIMIT });
				if (my === searchReq) found = page.items.map((t) => ({ id: t.id, value: t.target_value }));
			} catch {
				if (my === searchReq) found = [];
			}
		}, SEARCH_DELAY_MS);
		return () => clearTimeout(timer);
	});

	function pickTracker(id: string) {
		trackerId = id;
		destination = trackers.find((t) => t.id === id)?.destination ?? '';
		issueType = '';
	}

	async function save() {
		if (!project || !trackerId || !destination.trim()) return;
		saving = true;
		try {
			const route = await issueTrackersApi.setRoute({
				project_id: project.id,
				target_id: targetId === SELECT_NONE ? null : targetId,
				tracker_id: trackerId,
				destination: destination.trim(),
				issue_type: issueType.trim() || null
			});
			issueTrackers.upsertRoute(route);
			toast.success('Route saved');
			open = false;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Route not saved');
		} finally {
			saving = false;
		}
	}
</script>

<Dialog.Root bind:open={() => open, (next) => (next ? (open = true) : !saving && guard.close())}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>{editing ? 'Edit route' : 'Add route'}</Dialog.Title>
		</Dialog.Header>
		<div class="flex flex-col gap-4">
			<FormField
				label="Applies to"
				description={editing ? 'Read-only on an existing route.' : undefined}
			>
				{#snippet children({ id })}
					<Popover.Root bind:open={pickerOpen}>
						<Popover.Trigger class="w-full" disabled={!!editing}>
							{#snippet child({ props })}
								<Button
									{...props}
									{id}
									variant="outline"
									role="combobox"
									class="h-9 w-full justify-between font-normal"
								>
									<span class="min-w-0 truncate">
										{targetId === SELECT_NONE
											? `Every target in ${project?.name ?? ''}`
											: targetValue}
									</span>
									<ChevronsUpDownIcon class="size-4 shrink-0 text-muted-foreground" />
								</Button>
							{/snippet}
						</Popover.Trigger>
						<Popover.Content class="w-(--bits-popover-anchor-width) p-0" align="start">
							<Command.Root shouldFilter={false}>
								<Command.Input placeholder="Search targets" bind:value={search} />
								<Command.List class="max-h-72">
									<Command.Empty>No matches</Command.Empty>
									<Command.Group>
										<Command.Item
											value={SELECT_NONE}
											onSelect={() => {
												targetId = SELECT_NONE;
												targetValue = '';
												pickerOpen = false;
											}}
										>
											Every target
										</Command.Item>
										{#each found as target (target.id)}
											<Command.Item
												value={target.id}
												onSelect={() => {
													targetId = target.id;
													targetValue = target.value;
													pickerOpen = false;
												}}
											>
												<span class="min-w-0 truncate font-mono">{target.value}</span>
											</Command.Item>
										{/each}
									</Command.Group>
								</Command.List>
							</Command.Root>
						</Popover.Content>
					</Popover.Root>
				{/snippet}
			</FormField>
			<FormField label="Tracker">
				{#snippet children({ id })}
					<Select.Root type="single" value={trackerId} onValueChange={pickTracker}>
						<Select.Trigger {id} class="w-full"
							>{tracker?.name ?? 'Select a tracker'}</Select.Trigger
						>
						<Select.Content>
							{#each trackers as option (option.id)}
								<Select.Item value={option.id}>
									{option.name}{option.is_active ? '' : ' · Disabled'}
								</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				{/snippet}
			</FormField>
			{#if spec}
				<FormField label={spec.destinationLabel}>
					{#snippet children({ id })}
						<DestinationPicker
							{id}
							{trackerId}
							bind:value={destination}
							placeholder={spec.destinationPlaceholder}
							searchLabel={`Search ${pluralLabel(spec.destinationLabel).toLowerCase()}`}
						/>
					{/snippet}
				</FormField>
				{#if spec.hasIssueType}
					<FormField label="Issue type">
						{#snippet children({ id })}
							<DestinationPicker
								{id}
								kind="issue-type"
								{trackerId}
								{destination}
								bind:value={issueType}
								placeholder={tracker?.issue_type ?? 'Bug'}
								clearable
							/>
						{/snippet}
					</FormField>
				{/if}
			{/if}
		</div>
		<Dialog.Footer>
			<Button variant="outline" disabled={saving} onclick={() => guard.close()}>Cancel</Button>
			<LoadingButton
				loading={saving}
				loadingLabel="Saving"
				disabled={!trackerId || !destination.trim()}
				onclick={save}
			>
				Save
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
