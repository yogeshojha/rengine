<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import BellIcon from '@lucide/svelte/icons/bell';
	import CheckIcon from '@lucide/svelte/icons/check';
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import RotateCwIcon from '@lucide/svelte/icons/rotate-cw';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as InputGroup from '$lib/components/ui/input-group/index.js';
	import * as RadioGroup from '$lib/components/ui/radio-group/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { notificationChannelsStore } from '$lib/stores/notificationChannels.svelte';
	import { notificationChannelsApi } from '$lib/api/notificationChannels';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { settingsActions } from '$lib/stores/settings-actions.svelte';
	import {
		CHANNEL_LEVELS,
		DEFAULT_CHANNEL_LEVEL,
		channelEventsFor
	} from '$lib/config/notification-events';
	import {
		NOTIFICATION_PROVIDERS as PROVIDERS,
		notificationProviderMeta as metaFor,
		type ProviderMeta
	} from '$lib/config/notification-providers';
	import {
		defaultNotificationPreference,
		type NotificationChannelRead,
		type NotificationPreference,
		type NotifProvider
	} from '$lib/types/notification-channel';
	import { relativeTime } from '$lib/utilities/dates';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import { externalHref } from '$lib/utilities/links';
	import CheckStatus from './check-status.svelte';
	import { BODY_ROW, CHANNEL_COL, HEAD_ROW } from './columns';
	import type { CheckState } from './status';

	let loading = $state(true);
	let loadFailed = $state(false);
	let testingId = $state<string | null>(null);

	let dialogOpen = $state(false);
	let editingId = $state<string | null>(null);
	let formProvider = $state<NotifProvider>(PROVIDERS[0].provider);
	let formName = $state('');
	let formActive = $state(true);
	let formConfig = $state<Record<string, unknown>>({});
	let formMasked = $state<Record<string, boolean>>({});
	let formPref = $state<NotificationPreference>(defaultNotificationPreference());
	let revealed = $state<Record<string, boolean>>({});
	let saving = $state(false);
	let testingDraft = $state(false);
	let nameError = $state('');
	let eventsError = $state('');
	let fieldErrors = $state<Record<string, string>>({});
	let initial = $state('');

	let removing = $state<NotificationChannelRead | null>(null);
	let deleting = $state(false);

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const channels = $derived(notificationChannelsStore.channels);
	const events = $derived(channelEventsFor((c) => capabilitiesStore.has(c)));
	const formMeta = $derived(metaFor(formProvider));
	const levelLabel = $derived(
		CHANNEL_LEVELS.find((l) => l.value === formPref.min_severity)?.label ?? CHANNEL_LEVELS[0].label
	);
	const allEvents = $derived(events.every((e) => formPref.types.includes(e.type)));
	const configReady = $derived(
		formMeta.fields.every((field) => {
			if (!field.required || field.kind === 'bool' || field.default !== undefined) return true;
			if (field.kind === 'secret' && editingId && formMasked[field.key]) return true;
			return String(formConfig[field.key] ?? '').trim() !== '';
		})
	);
	const dirty = $derived(snapshot() !== initial);
	const guard = new DiscardGuard(
		() => dirty,
		() => (dialogOpen = false)
	);

	function snapshot(): string {
		return JSON.stringify([
			formProvider,
			formName.trim(),
			formActive,
			formConfig,
			[...formPref.types].sort(),
			formPref.min_severity
		]);
	}

	async function load() {
		loading = true;
		await notificationChannelsStore.fetch();
		loadFailed = !notificationChannelsStore.hasFetched;
		loading = false;
	}

	onMount(() => {
		if (!isAdmin) loading = false;
		else if (notificationChannelsStore.hasFetched) loading = false;
		else void load();
	});

	function eventSummary(channel: NotificationChannelRead): string {
		const chosen = events.filter((e) => channel.events?.types?.includes(e.type));
		if (chosen.length === events.length) return 'All events';
		if (chosen.length === 0) return 'No events';
		if (chosen.length <= 2) return chosen.map((e) => e.label).join(', ');
		return `${chosen.length} of ${events.length} events`;
	}

	function levelOf(channel: NotificationChannelRead): string {
		const value = channel.events?.min_severity ?? DEFAULT_CHANNEL_LEVEL;
		return CHANNEL_LEVELS.find((l) => l.value === value)?.label ?? value;
	}

	function delivery(channel: NotificationChannelRead): {
		check: CheckState;
		label: string;
		message: string | null;
	} {
		if (!channel.is_active) return { check: 'off', label: 'Disabled', message: null };
		if (channel.last_sent_at) {
			return {
				check: channel.last_sent_ok ? 'ok' : 'failed',
				label: channel.last_sent_ok
					? `Sent ${relativeTime(channel.last_sent_at)}`
					: `Failed ${relativeTime(channel.last_sent_at)}`,
				message: channel.last_sent_ok ? null : channel.last_sent_message
			};
		}
		if (channel.last_test_at) {
			return {
				check: channel.last_test_ok ? 'ok' : 'failed',
				label: `Tested ${relativeTime(channel.last_test_at)}`,
				message: channel.last_test_ok ? null : channel.last_test_message
			};
		}
		return { check: 'untested', label: 'Nothing sent', message: null };
	}

	function applyDefaults(meta: ProviderMeta) {
		const config: Record<string, unknown> = {};
		for (const field of meta.fields) {
			if (field.default !== undefined) config[field.key] = field.default;
		}
		formConfig = config;
		formMasked = {};
	}

	function clearErrors() {
		nameError = '';
		eventsError = '';
		fieldErrors = {};
		revealed = {};
	}

	function openAdd() {
		editingId = null;
		formProvider = PROVIDERS[0].provider;
		formName = '';
		formActive = true;
		formPref = defaultNotificationPreference();
		applyDefaults(PROVIDERS[0]);
		clearErrors();
		initial = snapshot();
		dialogOpen = true;
	}

	function openEdit(channel: NotificationChannelRead) {
		editingId = channel.id;
		formProvider = channel.provider as NotifProvider;
		formName = channel.name;
		formActive = channel.is_active;
		formConfig = {};
		formMasked = {};
		for (const field of metaFor(channel.provider).fields) {
			if (field.kind === 'secret') {
				formMasked[field.key] = (channel.config_masked[field.key] ?? '') !== '';
			} else if (channel.config_masked[field.key] !== undefined) {
				formConfig[field.key] = channel.config_masked[field.key];
			} else if (field.default !== undefined) {
				formConfig[field.key] = field.default;
			}
		}
		formPref = { ...defaultNotificationPreference(), ...channel.events };
		clearErrors();
		initial = snapshot();
		dialogOpen = true;
	}

	function setProvider(value: string) {
		formProvider = value as NotifProvider;
		applyDefaults(metaFor(value));
		fieldErrors = {};
	}

	function setField(key: string, value: unknown) {
		formConfig = { ...formConfig, [key]: value };
		formMasked = { ...formMasked, [key]: false };
		if (fieldErrors[key]) {
			const next = { ...fieldErrors };
			delete next[key];
			fieldErrors = next;
		}
	}

	function toggleEvent(type: string, on: boolean) {
		const rest = formPref.types.filter((t) => t !== type);
		formPref = { ...formPref, types: on ? [...rest, type] : rest };
		eventsError = '';
	}

	function toggleAll() {
		formPref = { ...formPref, types: allEvents ? [] : events.map((e) => e.type) };
		eventsError = '';
	}

	function buildConfig(): Record<string, unknown> | null {
		const out: Record<string, unknown> = {};
		const errors: Record<string, string> = {};
		for (const field of formMeta.fields) {
			const raw = formConfig[field.key];
			if (field.kind === 'bool') {
				out[field.key] = raw === undefined ? (field.default ?? false) : !!raw;
				continue;
			}
			if (field.kind === 'number') {
				if (raw === '' || raw === undefined) {
					if (field.default !== undefined) out[field.key] = Number(field.default);
					else if (field.required) errors[field.key] = `${field.label} is required`;
					continue;
				}
				const n = Number(raw);
				if (!Number.isFinite(n)) errors[field.key] = `${field.label} must be a number`;
				else out[field.key] = n;
				continue;
			}
			const value = String(raw ?? '').trim();
			if (value) out[field.key] = value;
			else if (field.kind === 'secret' && editingId) continue;
			else if (field.required) errors[field.key] = `${field.label} is required`;
		}
		fieldErrors = errors;
		return Object.keys(errors).length > 0 ? null : out;
	}

	async function save() {
		nameError = formName.trim() ? '' : 'Channel name is required';
		eventsError = formPref.types.length ? '' : 'Select at least one event';
		const config = buildConfig();
		if (config === null || nameError || eventsError) return;
		saving = true;
		try {
			if (editingId) {
				const updated = await notificationChannelsStore.update(editingId, {
					name: formName.trim(),
					is_active: formActive,
					...(Object.keys(config).length > 0 ? { config } : {}),
					events: formPref
				});
				if (updated) {
					toast.success('Channel saved');
					dialogOpen = false;
				}
			} else {
				const created = await notificationChannelsStore.create({
					name: formName.trim(),
					provider: formProvider,
					is_active: formActive,
					config,
					events: formPref
				});
				if (created) {
					toast.success('Channel added');
					dialogOpen = false;
				}
			}
		} finally {
			saving = false;
		}
	}

	async function testDraft() {
		const config = buildConfig();
		if (config === null) return;
		testingDraft = true;
		try {
			const result = await notificationChannelsApi.testConfig({ provider: formProvider, config });
			if (result.success) toast.success(result.message);
			else toast.error(result.message);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Test not sent');
		} finally {
			testingDraft = false;
		}
	}

	async function test(channel: NotificationChannelRead) {
		testingId = channel.id;
		try {
			const result = await notificationChannelsStore.test(channel.id);
			if (!result) return;
			if (result.success) toast.success(result.message);
			else toast.error(result.message);
		} finally {
			testingId = null;
		}
	}

	async function setActive(channel: NotificationChannelRead, active: boolean) {
		const updated = await notificationChannelsStore.update(channel.id, { is_active: active });
		if (updated) toast.success(`Channel ${active ? 'enabled' : 'disabled'}`);
	}

	async function remove() {
		const channel = removing;
		if (!channel) return;
		deleting = true;
		try {
			if (await notificationChannelsStore.remove(channel.id)) {
				toast.success('Channel removed');
				removing = null;
			}
		} finally {
			deleting = false;
		}
	}

	const hasRows = $derived(channels.length > 0);

	$effect(() => {
		if (!isAdmin || !hasRows) return;
		settingsActions.set(addAction);
		return () => settingsActions.clear(addAction);
	});
</script>

{#snippet addAction()}
	<Button size="sm" onclick={openAdd}>
		<PlusIcon class="size-4" />
		Add channel
	</Button>
{/snippet}

{#if !isAdmin}
	<EmptyState compact icon={BellIcon} title="Notifications are managed by administrators" />
{:else if loading}
	<Card.Root class="gap-3 p-4">
		<Skeleton class="h-8 w-full" />
		<Skeleton class="h-10 w-full" />
		<Skeleton class="h-10 w-full" />
	</Card.Root>
{:else if loadFailed}
	<EmptyState compact icon={TriangleAlertIcon} title="Notification channels not loaded">
		<Button variant="outline" size="sm" onclick={load}>
			<RotateCwIcon class="size-3.5" />
			Retry
		</Button>
	</EmptyState>
{:else if channels.length === 0}
	<EmptyState
		icon={BellIcon}
		title="No notification channels"
		description={PROVIDERS.map((p) => p.name).join(', ')}
	>
		<Button size="sm" onclick={openAdd}>
			<PlusIcon class="size-4" />
			Add channel
		</Button>
	</EmptyState>
{:else}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<div class="@container/channels w-full" role="table" aria-label="Notification channels">
			<div class={HEAD_ROW} role="row">
				<div class={CHANNEL_COL.channel} role="columnheader">Channel</div>
				<div class={CHANNEL_COL.events} role="columnheader">Events</div>
				<div class={CHANNEL_COL.level} role="columnheader">Minimum level</div>
				<div class={CHANNEL_COL.delivery} role="columnheader">Last delivery</div>
				<div class={CHANNEL_COL.actions} role="columnheader">
					<span class="sr-only">Actions</span>
				</div>
			</div>
			{#each channels as channel (channel.id)}
				{@const meta = metaFor(channel.provider)}
				{@const sent = delivery(channel)}
				<div class="{BODY_ROW} {channel.is_active ? '' : 'text-muted-foreground'}" role="row">
					<div class="{CHANNEL_COL.channel} flex flex-col" role="cell">
						<span class="text-sm leading-5 font-medium wrap-anywhere">{channel.name}</span>
						<span class="text-2xs text-muted-foreground">{meta.name}</span>
					</div>
					<div class="{CHANNEL_COL.events} text-sm" role="cell">{eventSummary(channel)}</div>
					<div class="{CHANNEL_COL.level} text-sm" role="cell">{levelOf(channel)}</div>
					<div class={CHANNEL_COL.delivery} role="cell">
						<CheckStatus
							check={sent.check}
							label={sent.label}
							message={sent.message}
							busy={testingId === channel.id}
							busyLabel="Sending"
							muted={sent.check !== 'failed'}
						/>
					</div>
					<div class={CHANNEL_COL.actions} role="cell">
						<DropdownMenu.Root>
							<DropdownMenu.Trigger>
								{#snippet child({ props })}
									<Button
										{...props}
										variant="ghost"
										size="icon"
										class="size-7"
										aria-label="{channel.name} actions"
									>
										<EllipsisIcon class="size-4" />
									</Button>
								{/snippet}
							</DropdownMenu.Trigger>
							<DropdownMenu.Content align="end">
								<DropdownMenu.Item
									disabled={testingId !== null || !channel.is_active}
									onSelect={() => test(channel)}
								>
									Send test
								</DropdownMenu.Item>
								<DropdownMenu.Item onSelect={() => openEdit(channel)}>Edit</DropdownMenu.Item>
								<DropdownMenu.Item onSelect={() => setActive(channel, !channel.is_active)}>
									{channel.is_active ? 'Disable' : 'Enable'}
								</DropdownMenu.Item>
								<DropdownMenu.Separator />
								<DropdownMenu.Item variant="destructive" onSelect={() => (removing = channel)}>
									Remove
								</DropdownMenu.Item>
							</DropdownMenu.Content>
						</DropdownMenu.Root>
					</div>
				</div>
			{/each}
		</div>
	</Card.Root>
{/if}

<Dialog.Root
	bind:open={() => dialogOpen, (next) => (next ? (dialogOpen = true) : !saving && guard.close())}
>
	<Dialog.Content
		class="grid max-h-[85vh] grid-rows-[auto_minmax(0,1fr)_auto] gap-0 overflow-hidden p-0 {editingId
			? 'sm:max-w-xl'
			: 'sm:max-w-3xl'}"
	>
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>{editingId ? 'Edit channel' : 'Add channel'}</Dialog.Title>
			<Dialog.Description>Where notifications are sent, and for which events.</Dialog.Description>
		</Dialog.Header>

		<div
			class="grid min-h-0 {editingId
				? 'grid-rows-[minmax(0,1fr)]'
				: 'grid-rows-[auto_minmax(0,1fr)] md:grid-cols-[212px_minmax(0,1fr)] md:grid-rows-1'}"
		>
			{#if !editingId}
				<div class="flex min-h-0 flex-col border-b bg-muted/20 md:border-r md:border-b-0">
					<ScrollArea class="md:min-h-0 md:flex-1">
						<RadioGroup.Root
							value={formProvider}
							onValueChange={setProvider}
							aria-label="Provider"
							class="flex flex-wrap gap-1.5 p-3 md:flex-col md:gap-0.5 md:p-2"
						>
							{#each PROVIDERS as p (p.provider)}
								{@const PIcon = p.icon}
								<Label
									class="group/provider flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm font-normal text-muted-foreground transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring/50 hover:bg-muted/60 hover:text-foreground data-[active=true]:bg-muted data-[active=true]:text-foreground"
									data-active={formProvider === p.provider}
								>
									<RadioGroup.Item value={p.provider} class="sr-only" disabled={saving} />
									<span
										class="flex size-7 shrink-0 items-center justify-center rounded-md border bg-background text-muted-foreground group-data-[active=true]/provider:border-primary/40 group-data-[active=true]/provider:text-primary"
									>
										<PIcon class="size-3.5" />
									</span>
									<span class="truncate">{p.name}</span>
									{#if formProvider === p.provider}
										<CheckIcon class="ml-auto hidden size-3.5 shrink-0 text-primary md:block" />
									{/if}
								</Label>
							{/each}
						</RadioGroup.Root>
					</ScrollArea>
				</div>
			{/if}

			<ScrollArea class="min-h-0">
				<div class="flex flex-col gap-6 px-6 py-5">
					<section class="flex flex-col gap-4">
						<div class="flex items-center justify-between gap-3">
							<SectionHead title={editingId ? formMeta.name : 'Connection'} />
							{#if formMeta.help}
								<a
									href={externalHref(formMeta.help.url)}
									target="_blank"
									rel="noopener noreferrer"
									class="inline-flex items-center gap-1 text-xs text-primary transition-colors hover:text-foreground"
								>
									{formMeta.help.label}<ExternalLinkIcon class="size-3" />
								</a>
							{/if}
						</div>

						<FormField label="Name" error={nameError} required>
							{#snippet children({ id })}
								<Input
									{id}
									bind:value={formName}
									placeholder="{formMeta.name} alerts"
									disabled={saving}
									aria-invalid={!!nameError}
									oninput={() => (nameError = '')}
								/>
							{/snippet}
						</FormField>

						<div class="grid gap-4 {formMeta.fields.length > 2 ? 'sm:grid-cols-2' : ''}">
							{#each formMeta.fields as field (field.key)}
								{#if field.kind === 'bool'}
									<label
										class="flex items-center justify-between rounded-md border px-3 py-2 sm:col-span-2"
										for="channel-{field.key}"
									>
										<span class="text-sm">{field.label}</span>
										<Switch
											id="channel-{field.key}"
											checked={formConfig[field.key] === undefined
												? !!field.default
												: !!formConfig[field.key]}
											onCheckedChange={(v) => setField(field.key, v)}
											disabled={saving}
										/>
									</label>
								{:else if field.kind === 'secret'}
									{@const stored = !!editingId && formMasked[field.key]}
									<FormField
										label={field.label}
										description={field.description}
										error={fieldErrors[field.key]}
										required={!!field.required && !stored}
										class="sm:col-span-2"
									>
										{#snippet children({ id })}
											<InputGroup.Root>
												<InputGroup.Addon>
													<KeyRoundIcon />
												</InputGroup.Addon>
												<InputGroup.Input
													{id}
													type={revealed[field.key] ? 'text' : 'password'}
													value={formConfig[field.key] === undefined
														? ''
														: String(formConfig[field.key])}
													placeholder={stored ? 'Stored' : (field.placeholder ?? '')}
													autocomplete="off"
													class="font-mono text-xs"
													disabled={saving}
													aria-invalid={!!fieldErrors[field.key]}
													oninput={(e) => setField(field.key, e.currentTarget.value)}
												/>
												<InputGroup.Addon align="inline-end">
													<InputGroup.Button
														size="icon-xs"
														aria-label={revealed[field.key] ? 'Hide value' : 'Show value'}
														aria-pressed={!!revealed[field.key]}
														onclick={() =>
															(revealed = { ...revealed, [field.key]: !revealed[field.key] })}
													>
														{#if revealed[field.key]}<EyeOffIcon />{:else}<EyeIcon />{/if}
													</InputGroup.Button>
												</InputGroup.Addon>
											</InputGroup.Root>
										{/snippet}
									</FormField>
								{:else}
									<FormField
										label={field.label}
										description={field.description}
										error={fieldErrors[field.key]}
										required={!!field.required && field.default === undefined}
									>
										{#snippet children({ id })}
											<Input
												{id}
												type={field.kind === 'number' ? 'number' : 'text'}
												value={formConfig[field.key] === undefined
													? ''
													: String(formConfig[field.key])}
												placeholder={field.placeholder ?? ''}
												autocomplete="off"
												class="font-mono text-xs"
												disabled={saving}
												aria-invalid={!!fieldErrors[field.key]}
												oninput={(e) => setField(field.key, e.currentTarget.value)}
											/>
										{/snippet}
									</FormField>
								{/if}
							{/each}
						</div>
					</section>

					<Separator />

					<section class="flex flex-col gap-3">
						<div class="flex items-center justify-between gap-3">
							<SectionHead title="Events" />
							<Button
								variant="link"
								size="sm"
								class="h-auto px-0 text-xs"
								onclick={toggleAll}
								disabled={saving}
							>
								{allEvents ? 'Clear all' : 'Select all'}
							</Button>
						</div>
						<div
							class="divide-y overflow-hidden rounded-lg border {eventsError
								? 'border-destructive'
								: ''}"
						>
							{#each events as event (event.type)}
								<Label
									class="flex cursor-pointer items-center gap-3 px-3 py-2.5 font-normal transition-colors hover:bg-muted/40"
								>
									<Checkbox
										checked={formPref.types.includes(event.type)}
										onCheckedChange={(v) => toggleEvent(event.type, v === true)}
										disabled={saving}
									/>
									<span class="flex min-w-0 flex-1 flex-col">
										<span class="text-sm font-medium">{event.label}</span>
										<span class="text-xs text-muted-foreground">{event.hint}</span>
									</span>
								</Label>
							{/each}
						</div>
						{#if eventsError}
							<p class="text-sm text-destructive" role="alert">{eventsError}</p>
						{/if}

						<div class="flex flex-wrap items-center justify-between gap-3 pt-1">
							<Label for="channel-level" class="text-sm">Minimum level</Label>
							<Select.Root
								type="single"
								value={formPref.min_severity}
								onValueChange={(v) =>
									(formPref = { ...formPref, min_severity: v ?? DEFAULT_CHANNEL_LEVEL })}
								disabled={saving}
							>
								<Select.Trigger id="channel-level" class="w-full sm:w-56">
									{levelLabel}
								</Select.Trigger>
								<Select.Content>
									{#each CHANNEL_LEVELS as level (level.value)}
										<Select.Item value={level.value} label={level.label}>{level.label}</Select.Item>
									{/each}
								</Select.Content>
							</Select.Root>
						</div>
					</section>
				</div>
			</ScrollArea>
		</div>

		<div class="flex flex-wrap items-center justify-between gap-3 border-t px-6 py-4">
			<div class="flex flex-wrap items-center gap-4">
				<Label class="cursor-pointer gap-3" for="channel-active">
					<Switch
						id="channel-active"
						checked={formActive}
						onCheckedChange={(v) => (formActive = v)}
						disabled={saving}
					/>
					<span class="text-sm font-medium">Active</span>
				</Label>
				{#if !editingId}
					<LoadingButton
						variant="ghost"
						loading={testingDraft}
						loadingLabel="Testing"
						disabled={saving || !configReady}
						onclick={testDraft}
					>
						Test connection
					</LoadingButton>
				{/if}
			</div>
			<div class="flex items-center gap-2">
				<Button variant="outline" onclick={() => guard.close()} disabled={saving}>Cancel</Button>
				<LoadingButton onclick={save} loading={saving} loadingLabel="Saving">
					{editingId ? 'Save' : 'Add channel'}
				</LoadingButton>
			</div>
		</div>
	</Dialog.Content>
</Dialog.Root>

<ConfirmDialog
	open={removing !== null}
	title="Remove channel"
	description={removing ? `Channel ${removing.name} is removed.` : ''}
	confirmLabel="Remove"
	loadingLabel="Removing"
	destructive
	loading={deleting}
	onOpenChange={(open) => {
		if (!open) removing = null;
	}}
	onConfirm={remove}
/>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
