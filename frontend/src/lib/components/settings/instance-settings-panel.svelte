<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import RotateCwIcon from '@lucide/svelte/icons/rotate-cw';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import EmptyState from '$lib/components/empty-state.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import SettingRow from './setting-row.svelte';
	import TimezonePicker from './timezone-picker.svelte';
	import { instanceSettingsStore } from '$lib/stores/instanceSettings.svelte';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { INSTANCE_MODES, MODE_LABELS, coerceInstanceMode } from '$lib/config/capabilities';
	import { AUTOMATIC, CONCURRENT_SCAN_CHOICES } from '$lib/config/scan-admission';
	import { SCAN_RETENTION, SCREENSHOT_RETENTION, retentionLabel } from '$lib/config/retention';
	import { SOURCE_NAME } from '$lib/config/infostealer';
	import type { InstanceSettingsUpdate } from '$lib/types/instance-settings';

	let loading = $state(true);
	let saving = $state(false);
	let name = $state('');
	let nameError = $state('');

	const settings = $derived(instanceSettingsStore.settings);
	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const locked = $derived(!isAdmin || saving);

	const automaticLabel = $derived(
		settings?.concurrent_scans_auto ? `Automatic · ${settings.concurrent_scans_auto}` : 'Automatic'
	);
	const concurrency = $derived([
		{ value: String(AUTOMATIC), label: automaticLabel },
		...CONCURRENT_SCAN_CHOICES.map((n) => ({ value: String(n), label: String(n) }))
	]);

	async function load() {
		loading = true;
		await instanceSettingsStore.fetch();
		loading = false;
	}

	onMount(() => {
		if (instanceSettingsStore.hasFetched) loading = false;
		else void load();
	});

	$effect(() => {
		const current = settings?.instance_name;
		if (current !== undefined) untrack(() => (name = current));
	});

	async function save(patch: InstanceSettingsUpdate, label: string) {
		saving = true;
		try {
			const updated = await instanceSettingsStore.update(patch);
			if (!updated) return null;
			capabilitiesStore.setMode(updated.mode);
			capabilitiesStore.setInstanceName(updated.instance_name);
			toast.success(`${label} saved`);
			return updated;
		} finally {
			saving = false;
		}
	}

	function commitName() {
		if (!settings) return;
		const next = name.trim();
		if (next === settings.instance_name) return;
		if (!next) {
			name = settings.instance_name;
			nameError = 'Instance name is required';
			return;
		}
		void save({ instance_name: next }, 'Instance name').then((updated) => {
			if (!updated && settings) name = settings.instance_name;
		});
	}
</script>

{#if loading && !settings}
	<Card.Root class="gap-3 p-5">
		<Skeleton class="h-4 w-24" />
		<Skeleton class="h-9 w-full" />
		<Skeleton class="h-9 w-full" />
		<Skeleton class="h-9 w-full" />
	</Card.Root>
{:else if !settings}
	<EmptyState compact icon={TriangleAlertIcon} title="Settings not loaded">
		<Button variant="outline" size="sm" onclick={load}>
			<RotateCwIcon class="size-3.5" />
			Retry
		</Button>
	</EmptyState>
{:else}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<div class="px-5 pt-4 pb-2"><SectionHead title="Instance" /></div>
		<SettingRow
			label="Name"
			help="Shown in browser tab titles"
			for="instance-name"
			class="border-t-0"
		>
			<div class="flex w-60 flex-col gap-3">
				<Input
					id="instance-name"
					bind:value={name}
					maxlength={120}
					autocomplete="off"
					class="h-9 w-60"
					disabled={locked}
					aria-invalid={!!nameError}
					aria-describedby={nameError ? 'instance-name-error' : undefined}
					oninput={() => (nameError = '')}
					onblur={commitName}
					onkeydown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
				/>
				{#if nameError}
					<p id="instance-name-error" class="text-sm text-destructive" role="alert">{nameError}</p>
				{/if}
			</div>
		</SettingRow>
		<SettingRow label="Time zone" help="Schedules and What's new dates" for="instance-timezone">
			<TimezonePicker
				id="instance-timezone"
				value={settings.timezone}
				disabled={locked}
				onChange={(zone) => save({ timezone: zone }, 'Time zone')}
			/>
		</SettingRow>
		<SettingRow
			label="Mode"
			help="Bug bounty adds Bounty Hub, program watches and recon presets"
			for="instance-mode"
		>
			<Select.Root
				type="single"
				value={coerceInstanceMode(settings.mode)}
				onValueChange={(v) => v && v !== settings.mode && save({ mode: v }, 'Mode')}
				disabled={locked}
			>
				<Select.Trigger id="instance-mode" class="h-9 w-60">
					{MODE_LABELS[coerceInstanceMode(settings.mode)]}
				</Select.Trigger>
				<Select.Content>
					{#each INSTANCE_MODES as mode (mode.value)}
						<Select.Item value={mode.value} label={mode.label}>{mode.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</SettingRow>

		<div class="border-t px-5 pt-4 pb-2"><SectionHead title="Scanning" /></div>
		<SettingRow
			label="Concurrent scans"
			help="Scans past the limit wait in launch order"
			for="instance-concurrency"
			class="border-t-0"
		>
			<Select.Root
				type="single"
				value={String(settings.concurrent_scans)}
				onValueChange={(v) =>
					v !== undefined &&
					Number(v) !== settings.concurrent_scans &&
					save({ concurrent_scans: Number(v) }, 'Concurrent scans')}
				disabled={locked}
			>
				<Select.Trigger id="instance-concurrency" class="h-9 w-60">
					{concurrency.find((o) => o.value === String(settings.concurrent_scans))?.label ??
						settings.concurrent_scans}
				</Select.Trigger>
				<Select.Content>
					{#each concurrency as option (option.value)}
						<Select.Item value={option.value} label={option.label}>{option.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</SettingRow>
		<SettingRow
			label="Re-check certificates"
			help="Refreshes certificate expiry between scans"
			for="instance-cert-recheck"
		>
			<Switch
				id="instance-cert-recheck"
				checked={settings.cert_recheck_enabled}
				disabled={locked}
				onCheckedChange={(v) => save({ cert_recheck_enabled: v }, 'Certificate re-check')}
			/>
		</SettingRow>
		<SettingRow
			label="Infostealer lookups"
			help="Sends each domain target to {SOURCE_NAME}"
			for="instance-infostealer"
		>
			<Switch
				id="instance-infostealer"
				checked={settings.infostealer_lookups}
				disabled={locked}
				onCheckedChange={(v) => save({ infostealer_lookups: v }, 'Infostealer lookups')}
			/>
		</SettingRow>

		<div class="border-t px-5 pt-4 pb-2"><SectionHead title="Retention" /></div>
		<SettingRow
			label="Scan history"
			help="Excludes the newest run of each target"
			for="instance-scan-retention"
			class="border-t-0"
		>
			<Select.Root
				type="single"
				value={String(settings.scan_history_retention_days)}
				onValueChange={(v) =>
					v !== undefined &&
					Number(v) !== settings.scan_history_retention_days &&
					save({ scan_history_retention_days: Number(v) }, 'Scan history retention')}
				disabled={locked}
			>
				<Select.Trigger id="instance-scan-retention" class="h-9 w-60">
					{retentionLabel(SCAN_RETENTION, String(settings.scan_history_retention_days))}
				</Select.Trigger>
				<Select.Content>
					{#each SCAN_RETENTION as option (option.value)}
						<Select.Item value={option.value} label={option.label}>{option.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</SettingRow>
		<SettingRow label="Screenshots and response bodies" for="instance-evidence-retention">
			<Select.Root
				type="single"
				value={String(settings.screenshot_retention_days)}
				onValueChange={(v) =>
					v !== undefined &&
					Number(v) !== settings.screenshot_retention_days &&
					save({ screenshot_retention_days: Number(v) }, 'Evidence retention')}
				disabled={locked}
			>
				<Select.Trigger id="instance-evidence-retention" class="h-9 w-60">
					{retentionLabel(SCREENSHOT_RETENTION, String(settings.screenshot_retention_days))}
				</Select.Trigger>
				<Select.Content>
					{#each SCREENSHOT_RETENTION as option (option.value)}
						<Select.Item value={option.value} label={option.label}>{option.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</SettingRow>

		{#if !isAdmin}
			<div class="border-t px-5 py-2.5 text-xs text-muted-foreground">
				Editable by administrators.
			</div>
		{/if}
	</Card.Root>
{/if}
