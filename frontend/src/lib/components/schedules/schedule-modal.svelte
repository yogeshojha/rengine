<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { AlertTriangle, CalendarClock, LoaderCircle } from 'lucide-svelte';

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

	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { scanSchedulesStore } from '$lib/stores/scan-schedules.svelte';
	import { instanceSettingsStore } from '$lib/stores/instanceSettings.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { targetsApi } from '$lib/api/targets';
	import {
		INTERVAL_UNITS,
		INTERVAL_UNIT_LABELS,
		type ScanScheduleCreate,
		type ScanScheduleRead,
		type ScheduleType
	} from '$lib/types/scan-schedule';
	import type { Target } from '$lib/types/target';

	interface Props {
		open: boolean;
		schedule?: ScanScheduleRead | null;
		presetTargetIds?: string[];
		onClose?: () => void;
	}

	let { open = $bindable(), schedule = null, presetTargetIds, onClose }: Props = $props();

	const NONE_CONTEXT = '__none__';

	let name = $state('');
	let targetIds = $state<string[]>([]);
	let engineId = $state('');
	let contextId = $state<string>(NONE_CONTEXT);
	let scheduleType = $state<ScheduleType>('daily_at');
	let onceLocal = $state('');
	let intervalEvery = $state('6');
	let intervalUnit = $state<string>('hours');
	let dailyTime = $state('10:00');
	let cronExpr = $state('0 0 * * *');

	let targets = $state<Target[]>([]);
	let targetsLoading = $state(false);
	let targetsError = $state<string | null>(null);
	let saving = $state(false);

	let isEdit = $derived(!!schedule);
	let timezone = $derived(instanceSettingsStore.settings?.timezone ?? 'UTC');

	let enginesReady = $derived(
		(scanEnginesStore.hasFetched || !!scanEnginesStore.error) && !scanEnginesStore.isLoading
	);
	let contextsReady = $derived(
		(scanContextsStore.hasFetched || !!scanContextsStore.error) && !scanContextsStore.isLoading
	);

	let engineLabel = $derived(
		scanEnginesStore.engines.find((e) => e.id === engineId)?.name ?? 'Select engine'
	);
	let contextLabel = $derived(
		contextId === NONE_CONTEXT
			? 'None — engine defaults'
			: (scanContextsStore.contexts.find((c) => c.id === contextId)?.name ?? 'Select context')
	);
	let targetItems = $derived(targets.map((t) => ({ id: t.id, label: t.target_value })));
	let selectedTargetItems = $derived(
		targetIds.map((id) => ({
			id,
			label: targets.find((t) => t.id === id)?.target_value ?? id
		}))
	);
	let unitLabel = $derived(
		INTERVAL_UNIT_LABELS[intervalUnit as keyof typeof INTERVAL_UNIT_LABELS] ?? 'Unit'
	);

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

	function prefill() {
		if (schedule) {
			name = schedule.name;
			targetIds = [...schedule.target_ids];
			engineId = schedule.engine_id;
			contextId = schedule.context_id ?? NONE_CONTEXT;
			scheduleType = schedule.schedule_type;
			onceLocal = schedule.run_at ? toLocalInput(schedule.run_at, timezone) : '';
			intervalEvery = schedule.interval_every ? String(schedule.interval_every) : '6';
			intervalUnit = schedule.interval_unit ?? 'hours';
			dailyTime = schedule.daily_at_time ?? '10:00';
			cronExpr = schedule.cron_expression ?? '0 0 * * *';
		} else {
			name = '';
			targetIds = presetTargetIds ? [...presetTargetIds] : [];
			engineId = '';
			contextId = NONE_CONTEXT;
			scheduleType = 'daily_at';
			onceLocal = '';
			intervalEvery = '6';
			intervalUnit = 'hours';
			dailyTime = '10:00';
			cronExpr = '0 0 * * *';
		}
	}

	$effect(() => {
		if (!open) return;
		const project = projectsStore.activeProject;
		if (!project) return;
		untrack(() => {
			prefill();
			if (!scanEnginesStore.hasFetched) scanEnginesStore.fetchEngines(project.id);
			if (!scanContextsStore.hasFetched) scanContextsStore.fetchContexts(project.id);
			if (!instanceSettingsStore.hasFetched) instanceSettingsStore.fetch();
			loadTargets(project.slug);
		});
	});

	async function loadTargets(projectSlug: string) {
		targetsLoading = true;
		targetsError = null;
		try {
			const res = await targetsApi.list({ project_slug: projectSlug, size: 100 });
			targets = res.items;
		} catch (e) {
			targetsError = e instanceof Error ? e.message : 'Failed to load targets';
		} finally {
			targetsLoading = false;
		}
	}

	function buildPayload(): ScanScheduleCreate {
		const base: ScanScheduleCreate = {
			name: name.trim(),
			target_ids: targetIds,
			engine_id: engineId,
			context_id: contextId === NONE_CONTEXT ? null : contextId,
			schedule_type: scheduleType
		};
		if (scheduleType === 'one_off') base.run_at = onceLocal;
		else if (scheduleType === 'interval') {
			base.interval_every = Number(intervalEvery);
			base.interval_unit = intervalUnit as ScanScheduleCreate['interval_unit'];
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
				toast.success(isEdit ? 'Schedule updated' : 'Schedule created');
				handleOpenChange(false);
			} else {
				toast.error(scanSchedulesStore.error ?? 'Failed to save schedule');
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

<Dialog.Root {open} onOpenChange={handleOpenChange}>
	<Dialog.Content class="flex max-h-[90vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-[560px]">
		<Dialog.Header class="p-6 pb-4">
			<Dialog.Title>{isEdit ? 'Edit scheduled scan' : 'New scheduled scan'}</Dialog.Title>
			<Dialog.Description>
				Keep these targets under continuous watch. reNgine re-runs the scan on your schedule and
				notifies you the moment new assets or vulnerabilities surface.
			</Dialog.Description>
		</Dialog.Header>

		<Separator />

		<ScrollArea class="min-h-0 flex-1">
			<div class="space-y-4 p-6">
				<div class="space-y-2">
					<Label for="schedule-name">Name <span class="text-destructive">*</span></Label>
					<Input id="schedule-name" bind:value={name} placeholder="Nightly recon" />
				</div>

				<div class="space-y-2">
					<Label for="schedule-targets">Targets <span class="text-destructive">*</span></Label>
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
							items={targetItems}
							selected={selectedTargetItems}
							onSelect={(item) =>
								(targetIds = targetIds.includes(item.id) ? targetIds : [...targetIds, item.id])}
							onRemove={(item) => (targetIds = targetIds.filter((id) => id !== item.id))}
							allowCreate={false}
							placeholder="Search targets…"
							emptyText="No targets in this project."
						/>
						<p class="text-[11px] text-muted-foreground">
							Each selected target runs as its own scan on every fire.
						</p>
					{/if}
				</div>

				<div class="grid grid-cols-2 gap-3">
					<div class="space-y-2">
						<Label for="schedule-engine">Engine <span class="text-destructive">*</span></Label>
						{#if !enginesReady}
							<Skeleton class="h-9 w-full rounded-md" />
						{:else}
							<Select.Root type="single" bind:value={engineId}>
								<Select.Trigger id="schedule-engine" class="w-full">{engineLabel}</Select.Trigger>
								<Select.Content>
									{#each scanEnginesStore.engines as engine (engine.id)}
										<Select.Item value={engine.id} label={engine.name}>{engine.name}</Select.Item>
									{/each}
								</Select.Content>
							</Select.Root>
						{/if}
					</div>
					<div class="space-y-2">
						<Label for="schedule-context">Context</Label>
						{#if !contextsReady}
							<Skeleton class="h-9 w-full rounded-md" />
						{:else}
							<Select.Root type="single" bind:value={contextId}>
								<Select.Trigger id="schedule-context" class="w-full">{contextLabel}</Select.Trigger>
								<Select.Content>
									<Select.Item value={NONE_CONTEXT} label="None — engine defaults">
										None — engine defaults
									</Select.Item>
									{#each scanContextsStore.contexts as context (context.id)}
										<Select.Item value={context.id} label={context.name}>{context.name}</Select.Item
										>
									{/each}
								</Select.Content>
							</Select.Root>
						{/if}
					</div>
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
							<Label for="daily-time" class="text-xs text-muted-foreground">Runs every day at</Label
							>
							<Input id="daily-time" type="time" bind:value={dailyTime} class="mt-1.5 w-40" />
						</Tabs.Content>

						<Tabs.Content value="interval" class="pt-3">
							<Label class="text-xs text-muted-foreground">Runs every</Label>
							<div class="mt-1.5 flex items-center gap-2">
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
						</Tabs.Content>

						<Tabs.Content value="one_off" class="pt-3">
							<Label for="once-at" class="text-xs text-muted-foreground">Runs once at</Label>
							<Input
								id="once-at"
								type="datetime-local"
								bind:value={onceLocal}
								class="mt-1.5 w-60"
							/>
						</Tabs.Content>

						<Tabs.Content value="cron" class="pt-3">
							<Label for="cron-expr" class="text-xs text-muted-foreground">Cron expression</Label>
							<Input
								id="cron-expr"
								bind:value={cronExpr}
								placeholder="0 0 * * *"
								class="mt-1.5 font-mono"
							/>
							<p class="mt-1 text-[11px] text-muted-foreground">
								Standard 5-field cron — minute, hour, day-of-month, month, day-of-week.
							</p>
						</Tabs.Content>
					</Tabs.Root>

					<div class="flex items-start gap-1.5 text-[11px] text-muted-foreground">
						<CalendarClock class="mt-px h-3.5 w-3.5 shrink-0" />
						<span>
							Scheduled times use your timezone
							<span class="font-medium text-foreground">{timezone}</span>
							— change it in
							<a href="/settings" class="underline underline-offset-2 hover:text-foreground"
								>Settings</a
							>.
						</span>
					</div>
				</div>
			</div>
		</ScrollArea>

		<Separator />

		<div class="flex items-center justify-end gap-3 bg-muted/30 p-4">
			<Button variant="outline" onclick={() => handleOpenChange(false)} disabled={saving}>
				Cancel
			</Button>
			<Button onclick={handleSave} disabled={!canSave} class="gap-2">
				{#if saving}<LoaderCircle class="h-4 w-4 animate-spin" />{/if}
				{isEdit ? 'Save changes' : 'Create schedule'}
			</Button>
		</div>
	</Dialog.Content>
</Dialog.Root>
