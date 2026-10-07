<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteMap } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';

	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import { Input } from '$lib/components/ui/input';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Select from '$lib/components/ui/select';
	import * as Tabs from '$lib/components/ui/tabs';
	import { Separator } from '$lib/components/ui/separator';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import MultiSelectCombobox from '$lib/components/multi-select-combobox.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';

	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import CredentialLock from '$lib/components/scans/launch/credential-lock.svelte';
	import {
		CONTEXT_NOUN,
		ENGINE_NOUN,
		credentialLaunchRefusal,
		launchLocked
	} from '$lib/config/launch';
	import { NO_CONTEXT_LABEL } from '$lib/types/scan-context';
	import { scanSchedulesStore } from '$lib/stores/scan-schedules.svelte';
	import { instanceSettingsStore } from '$lib/stores/instanceSettings.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { targetsApi } from '$lib/api/targets';
	import {
		INTERVAL_UNITS,
		INTERVAL_UNIT_LABELS,
		type IntervalUnit,
		type ScanScheduleCreate,
		type ScanScheduleRead,
		type ScheduleType
	} from '$lib/types/scan-schedule';
	import { ROUTES } from '$lib/config/routes';
	import { SELECT_NONE } from '$lib/constants';
	import type { Target } from '$lib/types/target';

	interface Props {
		open: boolean;
		schedule?: ScanScheduleRead | null;
		presetTargetIds?: string[];
		onClose?: () => void;
	}

	let { open = $bindable(), schedule = null, presetTargetIds, onClose }: Props = $props();

	let name = $state('');
	let targetIds = $state<string[]>([]);
	let engineId = $state('');
	let contextId = $state<string>(SELECT_NONE);
	let scheduleType = $state<ScheduleType>('daily_at');
	let onceLocal = $state('');
	let intervalEvery = $state('6');
	let intervalUnit = $state<IntervalUnit>('hours');
	let dailyTime = $state('10:00');
	let cronExpr = $state('0 0 * * *');

	let targets = $state<Target[]>([]);
	let targetsLoading = $state(false);
	let targetsError = $state<string | null>(null);
	const TARGET_ROWS = 50;
	const TARGET_SEARCH_DEBOUNCE_MS = 200;
	const targetNames = new SvelteMap<string, string>();
	let targetSeq = 0;
	let searchTimer: ReturnType<typeof setTimeout> | undefined;
	let saving = $state(false);

	let isEdit = $derived(!!schedule);
	let timezone = $derived(instanceSettingsStore.settings?.timezone ?? 'UTC');
	let zone = $derived(schedule?.timezone ?? timezone);

	let enginesReady = $derived(
		(scanEnginesStore.hasFetched || !!scanEnginesStore.error) && !scanEnginesStore.isLoading
	);
	let contextsReady = $derived(
		(scanContextsStore.hasFetched || !!scanContextsStore.error) && !scanContextsStore.isLoading
	);

	let engineLabel = $derived(
		scanEnginesStore.engines.find((e) => e.id === engineId)?.name ?? 'Select an engine'
	);
	let contextLabel = $derived(
		contextId === SELECT_NONE
			? NO_CONTEXT_LABEL
			: (scanContextsStore.contexts.find((c) => c.id === contextId)?.name ?? 'Select a context')
	);
	let targetItems = $derived(targets.map((t) => ({ id: t.id, label: t.target_value })));
	let selectedTargetItems = $derived(
		targetIds.map((id) => ({
			id,
			label: targetNames.get(id) ?? schedule?.targets.find((t) => t.id === id)?.target_value ?? id
		}))
	);
	let unitLabel = $derived(INTERVAL_UNIT_LABELS[intervalUnit] ?? 'Unit');

	let timingValid = $derived.by(() => {
		if (scheduleType === 'one_off') return !!onceLocal;
		if (scheduleType === 'interval') return Number(intervalEvery) >= 1;
		if (scheduleType === 'daily_at') return /^([01]\d|2[0-3]):[0-5]\d$/.test(dailyTime);
		if (scheduleType === 'cron') return cronExpr.trim().split(/\s+/).length >= 5;
		return false;
	});
	let canSave = $derived(
		!!name.trim() && targetIds.length > 0 && !!engineId && timingValid && !saving
	);

	function toLocalInput(iso: string, tz: string): string {
		const parts = new Intl.DateTimeFormat('en-CA', {
			timeZone: tz,
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
			hourCycle: 'h23'
		}).formatToParts(new Date(iso));
		const get = (t: string) => parts.find((p) => p.type === t)?.value ?? '';
		return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}`;
	}

	function snapshot(): string {
		return JSON.stringify([
			name.trim(),
			targetIds,
			engineId,
			contextId,
			scheduleType,
			onceLocal,
			String(intervalEvery),
			intervalUnit,
			dailyTime,
			cronExpr.trim()
		]);
	}

	let initial = $state('');
	let dirty = $derived(open && snapshot() !== initial);
	const guard = new DiscardGuard(
		() => dirty,
		() => handleOpenChange(false)
	);

	function prefill() {
		if (schedule) {
			name = schedule.name;
			targetIds = [...schedule.target_ids];
			engineId = schedule.engine_id;
			contextId = schedule.context_id ?? SELECT_NONE;
			scheduleType = schedule.schedule_type;
			onceLocal = schedule.run_at ? toLocalInput(schedule.run_at, schedule.timezone) : '';
			intervalEvery = schedule.interval_every ? String(schedule.interval_every) : '6';
			intervalUnit = schedule.interval_unit ?? 'hours';
			dailyTime = schedule.daily_at_time ?? '10:00';
			cronExpr = schedule.cron_expression ?? '0 0 * * *';
		} else {
			name = '';
			targetIds = presetTargetIds ? [...presetTargetIds] : [];
			engineId = '';
			contextId = SELECT_NONE;
			scheduleType = 'daily_at';
			onceLocal = '';
			intervalEvery = '6';
			intervalUnit = 'hours';
			dailyTime = '10:00';
			cronExpr = '0 0 * * *';
		}
		initial = snapshot();
	}

	$effect(() => {
		if (!open) return;
		const project = projectsStore.activeProject;
		if (!project) return;
		untrack(() => {
			prefill();
			if (scanEnginesStore.fetchedProjectId !== project.id)
				scanEnginesStore.fetchEngines(project.id);
			if (scanContextsStore.fetchedProjectId !== project.id)
				scanContextsStore.fetchContexts(project.id);
			if (!instanceSettingsStore.hasFetched) instanceSettingsStore.fetch();
			loadTargets(project.slug);
		});
	});

	async function fetchTargets(projectSlug: string, q: string): Promise<Target[] | null> {
		const mine = ++targetSeq;
		const res = await targetsApi.list({
			project_slug: projectSlug,
			search: q,
			sort_by: 'name',
			sort_dir: 'asc',
			size: TARGET_ROWS
		});
		if (mine !== targetSeq) return null;
		for (const t of res.items) targetNames.set(t.id, t.target_value);
		return res.items;
	}

	async function loadTargets(projectSlug: string) {
		targetsLoading = true;
		targetsError = null;
		try {
			targets = (await fetchTargets(projectSlug, '')) ?? targets;
		} catch (e) {
			targetsError = e instanceof Error ? e.message : 'Targets not loaded';
		} finally {
			targetsLoading = false;
		}
	}

	function searchTargets(q: string) {
		const slug = projectsStore.activeProject?.slug;
		if (!slug) return;
		clearTimeout(searchTimer);
		searchTimer = setTimeout(async () => {
			const found = await fetchTargets(slug, q).catch(() => null);
			if (found) targets = found;
		}, TARGET_SEARCH_DEBOUNCE_MS);
	}

	function buildPayload(): ScanScheduleCreate {
		const base: ScanScheduleCreate = {
			name: name.trim(),
			target_ids: targetIds,
			engine_id: engineId,
			context_id: contextId === SELECT_NONE ? null : contextId,
			schedule_type: scheduleType
		};
		if (scheduleType === 'one_off') base.run_at = onceLocal;
		else if (scheduleType === 'interval') {
			base.interval_every = Number(intervalEvery);
			base.interval_unit = intervalUnit;
		} else if (scheduleType === 'daily_at') base.daily_at_time = dailyTime;
		else if (scheduleType === 'cron') base.cron_expression = cronExpr.trim();
		return base;
	}

	async function handleSave() {
		const project = projectsStore.activeProject;
		if (!project || !canSave) return;
		saving = true;
		try {
			const payload = buildPayload();
			const result = schedule
				? await scanSchedulesStore.updateSchedule(schedule.id, project.id, payload)
				: await scanSchedulesStore.createSchedule(project.id, payload);
			if (result) {
				toast.success(isEdit ? 'Schedule saved' : 'Schedule created');
				handleOpenChange(false);
			} else {
				toast.error(scanSchedulesStore.error ?? 'Schedule not saved');
			}
		} finally {
			saving = false;
		}
	}

	function handleOpenChange(isOpen: boolean) {
		open = isOpen;
		if (!isOpen) onClose?.();
	}
</script>

<Dialog.Root
	bind:open={
		() => open,
		(next) => {
			if (next) open = true;
			else if (!saving) guard.close();
		}
	}
>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-xl">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>{isEdit ? 'Edit schedule' : 'New schedule'}</Dialog.Title>
			<Dialog.Description>Each target runs as its own scan on this schedule.</Dialog.Description>
		</Dialog.Header>

		<ScrollArea
			class="min-h-0 flex-1 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(85vh-10rem)]"
		>
			<div class="space-y-4 px-6 py-5">
				<FormField label="Name" required>
					{#snippet children({ id })}
						<Input {id} bind:value={name} placeholder="Nightly recon" />
					{/snippet}
				</FormField>

				<FormField label="Targets" required>
					{#snippet children({ id })}
						{#if targetsLoading}
							<Skeleton class="h-9 w-full rounded-md" />
						{:else if targetsError}
							<div
								class="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive"
							>
								<AlertTriangle class="h-3.5 w-3.5 shrink-0" />
								{targetsError}
							</div>
						{:else}
							<MultiSelectCombobox
								{id}
								items={targetItems}
								selected={selectedTargetItems}
								onSelect={(item) =>
									(targetIds = targetIds.includes(item.id) ? targetIds : [...targetIds, item.id])}
								onRemove={(item) => (targetIds = targetIds.filter((id) => id !== item.id))}
								onSearch={searchTargets}
								allowCreate={false}
								placeholder="Search targets"
								emptyText="No targets"
							/>
						{/if}
					{/snippet}
				</FormField>

				<div class="grid grid-cols-2 gap-3">
					<FormField label="Engine" required>
						{#snippet children({ id })}
							{#if !enginesReady}
								<Skeleton class="h-9 w-full rounded-md" />
							{:else}
								<Select.Root type="single" bind:value={engineId}>
									<Select.Trigger {id} class="w-full">{engineLabel}</Select.Trigger>
									<Select.Content>
										{#each scanEnginesStore.engines as engine (engine.id)}
											{@const locked = launchLocked(engine, auth.user)}
											<Select.Item value={engine.id} label={engine.name} disabled={locked}>
												{engine.name}
												{#if locked}
													<CredentialLock
														reason={credentialLaunchRefusal(ENGINE_NOUN, engine.name)}
													/>
												{/if}
											</Select.Item>
										{/each}
									</Select.Content>
								</Select.Root>
							{/if}
						{/snippet}
					</FormField>
					<FormField label="Context">
						{#snippet children({ id })}
							{#if !contextsReady}
								<Skeleton class="h-9 w-full rounded-md" />
							{:else}
								<Select.Root type="single" bind:value={contextId}>
									<Select.Trigger {id} class="w-full">{contextLabel}</Select.Trigger>
									<Select.Content>
										<Select.Item value={SELECT_NONE} label={NO_CONTEXT_LABEL}>
											{NO_CONTEXT_LABEL}
										</Select.Item>
										{#each scanContextsStore.contexts as context (context.id)}
											{@const locked = launchLocked(context, auth.user)}
											<Select.Item value={context.id} label={context.name} disabled={locked}>
												{context.name}
												{#if locked}
													<CredentialLock
														reason={credentialLaunchRefusal(CONTEXT_NOUN, context.name)}
													/>
												{/if}
											</Select.Item>
										{/each}
									</Select.Content>
								</Select.Root>
							{/if}
						{/snippet}
					</FormField>
				</div>

				<Separator />

				<div class="space-y-3">
					<Label>Schedule</Label>
					<Tabs.Root bind:value={scheduleType}>
						<Tabs.List class="grid w-full grid-cols-4">
							<Tabs.Trigger value="daily_at">Daily</Tabs.Trigger>
							<Tabs.Trigger value="interval">Interval</Tabs.Trigger>
							<Tabs.Trigger value="one_off">Once</Tabs.Trigger>
							<Tabs.Trigger value="cron">Cron</Tabs.Trigger>
						</Tabs.List>

						<Tabs.Content value="daily_at" class="pt-3">
							<FormField label="Runs every day at">
								{#snippet children({ id })}
									<Input {id} type="time" bind:value={dailyTime} class="max-w-40" />
								{/snippet}
							</FormField>
						</Tabs.Content>

						<Tabs.Content value="interval" class="pt-3">
							<div class="flex flex-col gap-3">
								<Label>Runs every</Label>
								<div class="flex items-center gap-2">
									<Input
										type="number"
										min="1"
										bind:value={intervalEvery}
										class="w-24"
										aria-label="Interval amount"
									/>
									<Select.Root type="single" bind:value={intervalUnit}>
										<Select.Trigger class="w-36">{unitLabel}</Select.Trigger>
										<Select.Content>
											{#each INTERVAL_UNITS as unit (unit)}
												<Select.Item value={unit} label={INTERVAL_UNIT_LABELS[unit]}>
													{INTERVAL_UNIT_LABELS[unit]}
												</Select.Item>
											{/each}
										</Select.Content>
									</Select.Root>
								</div>
							</div>
						</Tabs.Content>

						<Tabs.Content value="one_off" class="pt-3">
							<FormField label="Runs once at">
								{#snippet children({ id })}
									<Input {id} type="datetime-local" bind:value={onceLocal} class="max-w-60" />
								{/snippet}
							</FormField>
						</Tabs.Content>

						<Tabs.Content value="cron" class="pt-3">
							<FormField
								label="Cron expression"
								description="Standard 5-field cron: minute, hour, day of month, month, day of week."
							>
								{#snippet children({ id })}
									<Input {id} bind:value={cronExpr} placeholder="0 0 * * *" class="font-mono" />
								{/snippet}
							</FormField>
						</Tabs.Content>
					</Tabs.Root>

					<div class="flex items-start gap-1.5 text-2xs text-muted-foreground">
						<CalendarClock class="mt-px h-3.5 w-3.5 shrink-0" />
						<span>
							{#if isEdit}
								Scheduled times use the timezone
								<span class="font-medium text-foreground">{zone}</span>.
							{:else}
								Scheduled times use the instance timezone
								<span class="font-medium text-foreground">{zone}</span>. Change it in
								<a
									href={ROUTES.settings()}
									class="underline underline-offset-2 hover:text-foreground">Settings</a
								>.
							{/if}
						</span>
					</div>
				</div>
			</div>
		</ScrollArea>

		<Dialog.Footer class="border-t px-6 py-4">
			<Button variant="outline" onclick={() => guard.close()} disabled={saving}>Cancel</Button>
			<LoadingButton
				onclick={handleSave}
				disabled={!canSave}
				loading={saving}
				loadingLabel="Saving"
			>
				{isEdit ? 'Save' : 'Create schedule'}
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
