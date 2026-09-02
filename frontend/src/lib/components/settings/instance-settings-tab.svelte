<script lang="ts">
	import { onMount } from 'svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import { instanceSettingsStore } from '$lib/stores/instanceSettings.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { MASK } from '$lib/constants';
	import { AI_PROVIDERS, AI_FEATURES, DEFAULT_AI_PROVIDER } from '$lib/config/ai';
	import {
		INSTANCE_MODES,
		MODE_LABELS,
		DEFAULT_INSTANCE_MODE,
		coerceInstanceMode
	} from '$lib/config/capabilities';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as RadioGroup from '$lib/components/ui/radio-group/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { toast } from 'svelte-sonner';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
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
	let testing = $state(false);

	let instanceName = $state('reNgine');
	let timezone = $state('UTC');
	let mode = $state<string>(DEFAULT_INSTANCE_MODE);
	let scanRetention = $state('90');
	let screenshotRetention = $state('30');

	let aiEnabled = $state(false);
	let aiProvider = $state<string>(DEFAULT_AI_PROVIDER);
	let aiModel = $state('');
	let aiKey = $state('');
	let aiKeyMasked = $state<string | null>(null);
	let aiConfigured = $state(false);
	let showKey = $state(false);
	let aiFeatures = $state<Record<string, boolean>>({
		vuln_descriptions: true,
		impact_assessment: true,
		remediation: true,
		auto_report: false
	});

	let zoneOptions = $derived.by(() => {
		const local = Intl.DateTimeFormat().resolvedOptions().timeZone;
		if (local && !TIMEZONES.includes(local)) return [local, ...TIMEZONES];
		return TIMEZONES;
	});

	let modePlaceholder = $derived(
		INSTANCE_MODES.find((m) => m.value === mode)?.label ?? MODE_LABELS[DEFAULT_INSTANCE_MODE]
	);
	let aiModelPlaceholder = $derived(
		AI_PROVIDERS.find((p) => p.value === aiProvider)?.model ?? 'model name'
	);

	let snapshot = $state<string | null>(null);

	function currentState() {
		return JSON.stringify({
			instanceName: instanceName.trim(),
			timezone,
			mode,
			scanRetention,
			screenshotRetention,
			aiEnabled,
			aiProvider,
			aiModel: aiModel.trim(),
			aiKey: aiKey.trim(),
			aiFeatures
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
		aiEnabled = s.ai_enabled;
		aiProvider = s.ai_provider ?? DEFAULT_AI_PROVIDER;
		aiModel = s.ai_model ?? '';
		aiConfigured = s.ai_configured;
		aiKeyMasked = s.ai_api_key_masked;
		aiKey = '';
		if (s.ai_features && Object.keys(s.ai_features).length > 0) {
			aiFeatures = { ...aiFeatures, ...s.ai_features };
		}
		snapshot = currentState();
	}

	function selectProvider(v: string) {
		const prev = AI_PROVIDERS.find((p) => p.value === aiProvider);
		aiProvider = v;
		const meta = AI_PROVIDERS.find((p) => p.value === v);
		if (!meta) return;
		if (!aiModel.trim() || (prev && aiModel.trim() === prev.model)) aiModel = meta.model;
	}

	let modelMismatch = $derived.by(() => {
		const meta = AI_PROVIDERS.find((p) => p.value === aiProvider);
		return Boolean(meta && aiModel.trim() && aiModel.trim() !== meta.model);
	});

	async function handleSave() {
		if (!instanceSettingsStore.settings) {
			toast.error('Settings did not load — retry before saving');
			return;
		}
		if (!instanceName.trim()) {
			toast.error('Instance name is required');
			return;
		}
		if (aiEnabled && !aiConfigured && !aiKey.trim()) {
			toast.error('An API key is required to enable AI analysis');
			return;
		}

		saving = true;
		try {
			const aiKeyPayload = aiEnabled
				? aiKey.trim()
					? aiKey.trim()
					: aiConfigured
						? MASK
						: ''
				: undefined;

			const updated = await instanceSettingsStore.update({
				instance_name: instanceName.trim(),
				timezone,
				mode,
				scan_history_retention_days: Number(scanRetention),
				screenshot_retention_days: Number(screenshotRetention),
				ai_enabled: aiEnabled,
				ai_provider: aiEnabled ? aiProvider : undefined,
				ai_model: aiEnabled ? aiModel.trim() || null : undefined,
				...(aiKeyPayload !== undefined ? { ai_api_key: aiKeyPayload } : {}),
				...(aiEnabled ? { ai_features: aiFeatures } : {})
			});
			if (updated) {
				hydrate();
				toast.success('Settings saved');
			}
		} finally {
			saving = false;
		}
	}

	async function handleTestAi() {
		if (!aiKey.trim() && !aiConfigured) {
			toast.error('Enter an API key to test the connection');
			return;
		}
		testing = true;
		try {
			const result = await instanceSettingsStore.testAi({
				provider: aiProvider,
				model: aiModel.trim() || undefined,
				api_key: aiKey.trim() || undefined
			});
			if (!result) return;
			if (result.success) toast.success(result.message);
			else toast.error(result.message);
		} finally {
			testing = false;
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
			Instance identity, retention windows, and AI-powered analysis. Applies across all projects.
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
				<Empty.Title>Couldn't load settings</Empty.Title>
				<Empty.Description class="max-w-md">
					Instance settings failed to load. Editing now could overwrite your real configuration with
					defaults, so the form stays hidden until the load succeeds.
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
						Tunes available integrations and scoping. Bug Bounty unlocks HackerOne.
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
					<Card.Title class="text-base">AI-powered analysis</Card.Title>
				</div>
				<Card.Description
					>Enrich findings with descriptions, impact, and remediation via an external LLM.</Card.Description
				>
			</Card.Header>
			<Card.Content class="space-y-5">
				<div class="flex items-center justify-between rounded-lg border px-4 py-3">
					<div class="space-y-0.5">
						<Label class="text-sm font-medium">Enable AI-powered analysis</Label>
						<p class="text-xs text-muted-foreground">Connect an external LLM provider.</p>
					</div>
					<Switch checked={aiEnabled} onCheckedChange={(v) => (aiEnabled = v)} disabled={saving} />
				</div>

				{#if aiEnabled}
					<Alert.Root variant="destructive">
						<TriangleAlertIcon />
						<Alert.Title>Scan data leaves your instance</Alert.Title>
						<Alert.Description>
							Enabling AI sends scan data (targets, findings, and context) to your chosen external
							provider for processing. Do not enable this on air-gapped or sensitive deployments.
						</Alert.Description>
					</Alert.Root>

					<div class="space-y-2">
						<Label class="text-xs">Provider</Label>
						<RadioGroup.Root
							value={aiProvider}
							onValueChange={selectProvider}
							class="grid grid-cols-2 gap-2 sm:grid-cols-4"
						>
							{#each AI_PROVIDERS as p (p.value)}
								<Label
									class="flex cursor-pointer items-center gap-2 rounded-md border border-input bg-transparent px-3 py-2 text-sm data-[active=true]:border-primary data-[active=true]:bg-muted"
									data-active={aiProvider === p.value}
								>
									<RadioGroup.Item value={p.value} />
									<span class="truncate">{p.name}</span>
								</Label>
							{/each}
						</RadioGroup.Root>
					</div>

					<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
						<div class="space-y-1.5">
							<Label class="text-xs" for="ai-key">API key</Label>
							<div class="relative">
								<Input
									id="ai-key"
									type={showKey ? 'text' : 'password'}
									bind:value={aiKey}
									placeholder={aiConfigured
										? (aiKeyMasked ?? 'Leave blank to keep current key')
										: 'Paste your API key'}
									autocomplete="off"
									class="h-9 pr-9 font-mono text-xs"
									disabled={saving}
								/>
								<button
									type="button"
									class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
									onclick={() => (showKey = !showKey)}
									aria-label={showKey ? 'Hide key' : 'Show key'}
								>
									{#if showKey}<EyeOffIcon class="size-3.5" />{:else}<EyeIcon
											class="size-3.5"
										/>{/if}
								</button>
							</div>
							{#if aiConfigured}
								<p class="text-xs text-muted-foreground">
									Key set — leave blank to keep, or type to replace.
								</p>
							{/if}
						</div>
						<div class="space-y-1.5">
							<Label class="text-xs" for="ai-model">Model</Label>
							<Input
								id="ai-model"
								bind:value={aiModel}
								placeholder={aiModelPlaceholder}
								autocomplete="off"
								class="h-9 font-mono text-xs"
								disabled={saving}
							/>
							{#if modelMismatch}
								<p class="text-xs text-muted-foreground">
									Custom model — may not match {AI_PROVIDERS.find((p) => p.value === aiProvider)
										?.name}.
								</p>
							{/if}
						</div>
					</div>

					<div>
						<Button
							variant="outline"
							size="sm"
							class="h-8 text-xs"
							disabled={testing || saving || (!aiKey.trim() && !aiConfigured)}
							onclick={handleTestAi}
						>
							{#if testing}
								<Spinner class="mr-1.5 size-3" />
								Testing…
							{:else}
								<FlaskConicalIcon class="mr-1.5 size-3" />
								Test connection
							{/if}
						</Button>
					</div>

					<Separator />

					<div class="space-y-3">
						<Label class="text-xs">Features</Label>
						<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
							{#each AI_FEATURES as f (f.key)}
								<Label
									class="flex cursor-pointer items-start gap-3 rounded-md border border-input px-3 py-2.5 data-[active=true]:border-primary data-[active=true]:bg-muted"
									data-active={aiFeatures[f.key]}
								>
									<Checkbox
										checked={aiFeatures[f.key]}
										onCheckedChange={(v) => (aiFeatures = { ...aiFeatures, [f.key]: v === true })}
										class="mt-0.5"
									/>
									<span class="space-y-0.5">
										<span class="block text-sm font-medium">{f.label}</span>
										<span class="block text-xs text-muted-foreground">{f.hint}</span>
									</span>
								</Label>
							{/each}
						</div>
					</div>
				{/if}
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
