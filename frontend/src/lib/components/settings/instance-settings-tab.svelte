<script lang="ts">
	import { ROUTES } from '$lib/config/routes';
	import { onMount } from 'svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import { instanceSettingsStore } from '$lib/stores/instanceSettings.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import {
		INSTANCE_MODES,
		MODE_LABELS,
		DEFAULT_INSTANCE_MODE,
		coerceInstanceMode
	} from '$lib/config/capabilities';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { toast } from 'svelte-sonner';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import RotateCwIcon from '@lucide/svelte/icons/rotate-cw';

	const TIMEZONES = [
		'UTC',
		'America/New_York',
		'America/Chicago',
		'America/Denver',
		'America/Los_Angeles',
		'America/Sao_Paulo',
		'Europe/London',
		'Europe/Paris',
		'Europe/Berlin',
		'Europe/Moscow',
		'Asia/Dubai',
		'Asia/Kolkata',
		'Asia/Singapore',
		'Asia/Shanghai',
		'Asia/Tokyo',
		'Australia/Sydney'
	];

	const SCAN_RETENTION = [
		{ value: '30', label: '30 days' },
		{ value: '60', label: '60 days' },
		{ value: '90', label: '90 days' },
		{ value: '180', label: '180 days' },
		{ value: '365', label: '1 year' }
	];

	const SCREENSHOT_RETENTION = [
		{ value: '7', label: '7 days' },
		{ value: '14', label: '14 days' },
		{ value: '30', label: '30 days' },
		{ value: '60', label: '60 days' },
		{ value: '90', label: '90 days' }
	];

	let isLoading = $state(true);
	let loadFailed = $state(false);
	let saving = $state(false);

	let instanceName = $state('reNgine');
	let timezone = $state('UTC');
	let mode = $state<string>(DEFAULT_INSTANCE_MODE);
	let scanRetention = $state('90');
	let screenshotRetention = $state('30');

	let zoneOptions = $derived.by(() => {
		const local = Intl.DateTimeFormat().resolvedOptions().timeZone;
		if (local && !TIMEZONES.includes(local)) return [local, ...TIMEZONES];
		return TIMEZONES;
	});

	let modePlaceholder = $derived(
		INSTANCE_MODES.find((m) => m.value === mode)?.label ?? MODE_LABELS[DEFAULT_INSTANCE_MODE]
	);
	let snapshot = $state<string | null>(null);

	function currentState() {
		return JSON.stringify({
			instanceName: instanceName.trim(),
			timezone,
			mode,
			scanRetention,
			screenshotRetention
		});
	}

	let isDirty = $derived(snapshot !== null && currentState() !== snapshot);

	function hydrate() {
		const s = instanceSettingsStore.settings;
		if (!s) return;
		instanceName = s.instance_name;
		timezone = s.timezone;
		mode = coerceInstanceMode(s.mode);
		scanRetention = String(s.scan_history_retention_days);
		screenshotRetention = String(s.screenshot_retention_days);
		snapshot = currentState();
	}

	async function handleSave() {
		if (!instanceSettingsStore.settings) {
			toast.error('Settings did not load. Retry before saving.');
			return;
		}
		if (!instanceName.trim()) {
			toast.error('Instance name is required');
			return;
		}
		saving = true;
		try {
			const updated = await instanceSettingsStore.update({
				instance_name: instanceName.trim(),
				timezone,
				mode,
				scan_history_retention_days: Number(scanRetention),
				screenshot_retention_days: Number(screenshotRetention)
			});
			if (updated) {
				hydrate();
				toast.success('Settings saved');
			}
		} finally {
			saving = false;
		}
	}

	async function load() {
		isLoading = true;
		loadFailed = false;
		if (!instanceSettingsStore.hasFetched) await instanceSettingsStore.fetch();
		if (instanceSettingsStore.settings) hydrate();
		else loadFailed = true;
		isLoading = false;
	}

	onMount(load);

	let showLeaveDialog = $state(false);
	let pendingNav: (() => void) | null = $state(null);
	let allowNavigation = $state(false);

	beforeNavigate((nav) => {
		if (allowNavigation) {
			allowNavigation = false;
			return;
		}
		if (!isDirty || saving || pendingNav) return;
		nav.cancel();
		pendingNav = () => {
			allowNavigation = true;
			if (nav.to) goto(nav.to.url);
		};
		showLeaveDialog = true;
	});

	$effect(() => {
		if (typeof window === 'undefined') return;
		function onBeforeUnload(e: BeforeUnloadEvent) {
			if (!isDirty || saving) return;
			e.preventDefault();
		}
		window.addEventListener('beforeunload', onBeforeUnload);
		return () => window.removeEventListener('beforeunload', onBeforeUnload);
	});
</script>

<div class="space-y-6">
	<div>
		<h3 class="text-lg font-semibold">General</h3>
		<p class="text-sm text-muted-foreground">
			Instance identity, retention windows and AI analysis. Applies across all projects.
		</p>
	</div>

	<Separator />

	{#if isLoading}
		<div class="space-y-4">
			<Skeleton class="h-40 w-full rounded-xl" />
			<Skeleton class="h-40 w-full rounded-xl" />
		</div>
	{:else if loadFailed}
		<Empty.Root class="border bg-muted/20 py-16">
			<Empty.Header>
				<Empty.Media class="size-14 rounded-2xl bg-destructive/10">
					<CircleAlertIcon class="size-7 text-destructive" />
				</Empty.Media>
				<Empty.Title>Settings could not be loaded</Empty.Title>
				<Empty.Description class="max-w-md">
					Instance settings failed to load. Editing now could overwrite the stored configuration
					with defaults, so the form stays hidden until the load succeeds.
				</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button onclick={load} class="gap-2">
					<RotateCwIcon class="size-4" />
					Retry
				</Button>
			</Empty.Content>
		</Empty.Root>
	{:else}
		<Card.Root>
			<Card.Header>
				<Card.Title class="text-base">Instance</Card.Title>
				<Card.Description
					>Identify this deployment and set its default time zone and posture.</Card.Description
				>
			</Card.Header>
			<Card.Content class="space-y-5">
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<div class="space-y-1.5">
						<Label class="text-xs" for="instance-name">Instance name</Label>
						<Input
							id="instance-name"
							bind:value={instanceName}
							placeholder="reNgine"
							class="h-9"
							disabled={saving}
						/>
					</div>
					<div class="space-y-1.5">
						<Label class="text-xs">Time zone</Label>
						<Select.Root type="single" bind:value={timezone}>
							<Select.Trigger class="h-9 w-full text-sm">{timezone}</Select.Trigger>
							<Select.Content>
								{#each zoneOptions as tz (tz)}
									<Select.Item value={tz} label={tz}>{tz}</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
					</div>
				</div>

				<div class="space-y-1.5">
					<Label class="text-xs">Mode</Label>
					<Select.Root type="single" bind:value={mode}>
						<Select.Trigger class="h-9 w-full text-sm sm:w-72">{modePlaceholder}</Select.Trigger>
						<Select.Content>
							{#each INSTANCE_MODES as m (m.value)}
								<Select.Item value={m.value} label={m.label}>{m.label}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
					<p class="text-xs text-muted-foreground">
						Sets which integrations and scoping options appear. Bug bounty adds HackerOne.
					</p>
				</div>
			</Card.Content>
		</Card.Root>

		<Card.Root>
			<Card.Header>
				<Card.Title class="text-base">Data retention</Card.Title>
				<Card.Description
					>How long scan history and screenshots are kept before pruning.</Card.Description
				>
			</Card.Header>
			<Card.Content>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<div class="space-y-1.5">
						<Label class="text-xs">Scan history</Label>
						<Select.Root type="single" bind:value={scanRetention}>
							<Select.Trigger class="h-9 w-full text-sm">
								{SCAN_RETENTION.find((o) => o.value === scanRetention)?.label ?? '90 days'}
							</Select.Trigger>
							<Select.Content>
								{#each SCAN_RETENTION as o (o.value)}
									<Select.Item value={o.value} label={o.label}>{o.label}</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
					</div>
					<div class="space-y-1.5">
						<Label class="text-xs">Screenshots</Label>
						<Select.Root type="single" bind:value={screenshotRetention}>
							<Select.Trigger class="h-9 w-full text-sm">
								{SCREENSHOT_RETENTION.find((o) => o.value === screenshotRetention)?.label ??
									'30 days'}
							</Select.Trigger>
							<Select.Content>
								{#each SCREENSHOT_RETENTION as o (o.value)}
									<Select.Item value={o.value} label={o.label}>{o.label}</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
					</div>
				</div>
			</Card.Content>
		</Card.Root>

		<Card.Root>
			<Card.Header>
				<div class="flex items-center gap-2">
					<SparklesIcon class="size-4 text-foreground" />
					<Card.Title class="text-base">AI</Card.Title>
				</div>
				<Card.Description>
					Model connection, feature opt-ins and cost are configured on the AI page.
				</Card.Description>
			</Card.Header>
			<Card.Content>
				<Button variant="outline" size="sm" href={ROUTES.ai()}>
					<SparklesIcon class="mr-1.5 size-3.5" />
					Open the AI page
				</Button>
			</Card.Content>
		</Card.Root>

		<div class="flex items-center justify-end gap-3">
			{#if isDirty}
				<span class="text-xs text-muted-foreground">Unsaved changes</span>
			{/if}
			<Button onclick={handleSave} disabled={saving || !isDirty}>
				{#if saving}
					<Spinner class="mr-2" />
					Saving…
				{:else}
					Save changes
				{/if}
			</Button>
		</div>
	{/if}
</div>

<UnsavedChangesDialog
	bind:open={showLeaveDialog}
	onOpenChange={(o) => {
		showLeaveDialog = o;
		if (!o) pendingNav = null;
	}}
	onConfirm={() => {
		showLeaveDialog = false;
		const resume = pendingNav;
		pendingNav = null;
		resume?.();
	}}
/>
