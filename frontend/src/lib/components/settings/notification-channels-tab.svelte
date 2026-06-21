<script lang="ts">
	import { onMount } from 'svelte';
	import { notificationChannelsStore } from '$lib/stores/notificationChannels.svelte';
	import {
		NOTIF_CATEGORIES,
		NOTIF_SEVERITIES,
		defaultNotificationPreference,
		type NotificationChannelRead,
		type NotificationPreference,
		type NotifProvider
	} from '$lib/types/notification-channel';
	import {
		NOTIFICATION_PROVIDERS as PROVIDERS,
		notificationProviderMeta as metaFor,
		type ProviderMeta
	} from '$lib/config/notification-providers';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import * as RadioGroup from '$lib/components/ui/radio-group/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { toast } from 'svelte-sonner';
	import BellIcon from '@lucide/svelte/icons/bell';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import { formatDate } from '$lib/utilities';
	import { SvelteSet } from 'svelte/reactivity';

	let isLoading = $state(true);
	let testingId = $state<string | null>(null);

	let dialogOpen = $state(false);
	let editingId = $state<string | null>(null);
	let formProvider = $state<NotifProvider>('slack');
	let formName = $state('');
	let formActive = $state(true);
	let formConfig = $state<Record<string, unknown>>({});
	let formMasked = $state<Record<string, boolean>>({});
	let formPref = $state<NotificationPreference>(defaultNotificationPreference());
	let saving = $state(false);

	let nameError = $state('');
	let categoryError = $state('');
	let fieldErrors = $state<Record<string, string>>({});

	let deleteOpen = $state(false);
	let deletingChannel = $state<NotificationChannelRead | null>(null);
	let isDeleting = $state(false);

	let channels = $derived(notificationChannelsStore.channels);
	let formMeta = $derived(metaFor(formProvider));
	let severityLabel = $derived(
		NOTIF_SEVERITIES.find((s) => s.value === formPref.min_severity)?.label ?? 'Everything'
	);

	function applyDefaults(meta: ProviderMeta) {
		const cfg: Record<string, unknown> = {};
		for (const f of meta.fields) {
			if (f.default !== undefined) cfg[f.key] = f.default;
		}
		formConfig = cfg;
		formMasked = {};
	}

	function clearErrors() {
		nameError = '';
		categoryError = '';
		fieldErrors = {};
	}

	function openAdd() {
		editingId = null;
		formProvider = 'slack';
		formName = '';
		formActive = true;
		formPref = defaultNotificationPreference();
		applyDefaults(metaFor('slack'));
		clearErrors();
		dialogOpen = true;
	}

	function openEdit(c: NotificationChannelRead) {
		editingId = c.id;
		formProvider = c.provider as NotifProvider;
		formName = c.name;
		formActive = c.is_active;
		formConfig = {};
		formMasked = {};
		const meta = metaFor(c.provider);
		for (const f of meta.fields) {
			if (f.kind === 'secret') {
				formMasked[f.key] = (c.config_masked[f.key] ?? '') !== '';
			} else if (c.config_masked[f.key] !== undefined) {
				formConfig[f.key] = c.config_masked[f.key];
			} else if (f.default !== undefined) {
				formConfig[f.key] = f.default;
			}
		}
		formPref = { ...defaultNotificationPreference(), ...c.events };
		clearErrors();
		dialogOpen = true;
	}

	function setProvider(v: string) {
		formProvider = v as NotifProvider;
		applyDefaults(metaFor(v));
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

	function toggleCategory(value: string, on: boolean) {
		const set = new SvelteSet(formPref.types);
		if (on) set.add(value);
		else set.delete(value);
		formPref = { ...formPref, types: [...set] };
		if (categoryError) categoryError = '';
	}

	function buildConfig(): Record<string, unknown> | null {
		const out: Record<string, unknown> = {};
		const errors: Record<string, string> = {};
		for (const f of formMeta.fields) {
			const raw = formConfig[f.key];
			if (f.kind === 'bool') {
				out[f.key] = raw === undefined ? (f.default ?? false) : !!raw;
				continue;
			}
			if (f.kind === 'number') {
				if (raw === '' || raw === undefined) {
					if (f.default !== undefined) out[f.key] = Number(f.default);
					else if (f.required) errors[f.key] = `${f.label} is required`;
					continue;
				}
				const n = Number(raw);
				if (!Number.isFinite(n)) errors[f.key] = `${f.label} must be a number`;
				else out[f.key] = n;
				continue;
			}
			const val = String(raw ?? '').trim();
			if (val) {
				out[f.key] = val;
			} else if (f.kind === 'secret' && editingId) {
				continue;
			} else if (f.required) {
				errors[f.key] = `${f.label} is required`;
			}
		}
		fieldErrors = errors;
		return Object.keys(errors).length > 0 ? null : out;
	}

	async function handleSave() {
		nameError = '';
		categoryError = '';
		let invalid = false;
		if (!formName.trim()) {
			nameError = 'Channel name is required';
			invalid = true;
		}
		if (formPref.types.length === 0) {
			categoryError = 'Select at least one notification category';
			invalid = true;
		}
		const config = buildConfig();
		if (config === null || invalid) {
			toast.error('Please fix the highlighted fields');
			return;
		}

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
					toast.success('Channel updated');
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

	async function handleTest(id: string) {
		testingId = id;
		try {
			const result = await notificationChannelsStore.test(id);
			if (!result) return;
			if (result.success) toast.success(result.message);
			else toast.error(result.message);
		} finally {
			testingId = null;
		}
	}

	function openDelete(c: NotificationChannelRead) {
		deletingChannel = c;
		deleteOpen = true;
	}

	async function handleDelete() {
		if (!deletingChannel) return;
		isDeleting = true;
		try {
			const ok = await notificationChannelsStore.remove(deletingChannel.id);
			if (ok) {
				toast.success('Channel removed');
				deleteOpen = false;
			}
		} finally {
			isDeleting = false;
		}
	}

	function summaryLine(c: NotificationChannelRead): string {
		const n = c.events?.types?.length ?? 0;
		return `${n} categor${n === 1 ? 'y' : 'ies'}`;
	}

	onMount(async () => {
		if (!notificationChannelsStore.hasFetched) await notificationChannelsStore.fetch();
		isLoading = false;
	});
</script>

<div class="space-y-6">
	<div class="flex items-start justify-between">
		<div>
			<h3 class="text-lg font-semibold">Notifications</h3>
			<p class="text-sm text-muted-foreground">
				Route recon &amp; scan events to your team. Powered by Apprise — Slack, Discord, Telegram,
				Teams, email, webhooks, and 100+ more via a custom URL.
			</p>
		</div>
		<Button size="sm" onclick={openAdd}>
			<PlusIcon class="mr-1.5 size-4" />
			Add channel
		</Button>
	</div>

	<Separator />

	{#if isLoading}
		<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
			{#each Array(3) as _, i (i)}
				<Card.Root>
					<Card.Content class="p-5">
						<div class="flex items-start gap-3">
							<Skeleton class="size-10 rounded-lg" />
							<div class="flex-1 space-y-2">
								<Skeleton class="h-5 w-28" />
								<Skeleton class="h-4 w-full" />
							</div>
						</div>
					</Card.Content>
				</Card.Root>
			{/each}
		</div>
	{:else if channels.length === 0}
		<Card.Root class="border-dashed">
			<Card.Content class="flex flex-col items-center justify-center gap-3 py-16 text-center">
				<BellIcon class="size-10 text-muted-foreground/40" />
				<div class="space-y-1">
					<p class="text-sm font-medium">No notification channels</p>
					<p class="text-xs text-muted-foreground">
						Connect Slack, Discord, Telegram, Teams, email, or any Apprise target to get alerts.
					</p>
				</div>
				<Button size="sm" variant="outline" onclick={openAdd}>
					<PlusIcon class="mr-1.5 size-4" />
					Add channel
				</Button>
			</Card.Content>
		</Card.Root>
	{:else}
		<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
			{#each channels as channel (channel.id)}
				{@const meta = metaFor(channel.provider)}
				{@const Icon = meta.icon}
				<Card.Root class="relative transition-all duration-200 {channel.is_active ? 'ring-1 ring-border' : 'border-dashed opacity-75'}">
					<Card.Content class="p-5">
						<div class="flex items-start justify-between gap-3">
							<div class="flex min-w-0 items-start gap-3">
								<div class="shrink-0 rounded-lg border bg-muted p-2.5">
									<Icon class="size-[18px] text-muted-foreground" />
								</div>
								<div class="min-w-0">
									<h4 class="truncate text-sm font-medium">{channel.name}</h4>
									<p class="mt-0.5 text-xs text-muted-foreground">{meta.name}</p>
								</div>
							</div>
							<Switch
								checked={channel.is_active}
								onCheckedChange={(checked) =>
									notificationChannelsStore.update(channel.id, { is_active: checked }).then((u) => {
										if (u) toast.success(checked ? 'Channel enabled' : 'Channel disabled');
									})}
							/>
						</div>

						<Separator class="my-3" />

						<div class="space-y-2">
							{#each meta.fields.filter((f) => f.kind !== 'bool') as f (f.key)}
								<div class="flex items-center gap-2 text-xs">
									<span class="shrink-0 text-muted-foreground">{f.label}</span>
									<code class="truncate font-mono text-muted-foreground">{String(channel.config_masked[f.key] ?? '—')}</code>
								</div>
							{/each}
							<div class="flex flex-wrap items-center gap-2 pt-1">
								<Badge variant="secondary" class="h-5 border-0 px-1.5 text-[10px]">
									{summaryLine(channel)}
								</Badge>
								{#if channel.last_test_at}
									<span class="flex items-center gap-1 text-xs text-muted-foreground">
										{#if channel.last_test_ok}
											<CheckIcon class="size-3 text-foreground" />
										{:else}
											<CircleXIcon class="size-3 text-destructive" />
										{/if}
										{formatDate(channel.last_test_at)}
									</span>
								{/if}
							</div>
						</div>

						<div class="mt-3 flex items-center gap-1.5">
							<Button variant="ghost" size="sm" class="h-7 px-2 text-xs" onclick={() => openEdit(channel)}>
								<Pencil class="mr-1 size-3" />
								Edit
							</Button>
							<Button
								variant="ghost"
								size="sm"
								class="h-7 px-2 text-xs"
								disabled={testingId === channel.id}
								onclick={() => handleTest(channel.id)}
							>
								{#if testingId === channel.id}
									<Spinner class="mr-1 size-3" />
								{:else}
									<FlaskConicalIcon class="mr-1 size-3" />
								{/if}
								Test
							</Button>
							<div class="flex-1"></div>
							<Tooltip.Root>
								<Tooltip.Trigger>
									{#snippet child({ props })}
										<Button
											{...props}
											variant="ghost"
											size="sm"
											class="h-7 px-2 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
											onclick={() => openDelete(channel)}
										>
											<Trash2Icon class="size-3" />
										</Button>
									{/snippet}
								</Tooltip.Trigger>
								<Tooltip.Content>Remove channel</Tooltip.Content>
							</Tooltip.Root>
						</div>
					</Card.Content>
				</Card.Root>
			{/each}
		</div>
	{/if}
</div>

<Dialog.Root bind:open={dialogOpen}>
	<Dialog.Content class="flex max-h-[88vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg">
		<Dialog.Header class="px-6 pt-6 pb-2">
			<Dialog.Title>{editingId ? 'Edit channel' : 'Add channel'}</Dialog.Title>
			<Dialog.Description>Connect a provider and choose which events reach it.</Dialog.Description>
		</Dialog.Header>

		<ScrollArea class="flex-1">
			<div class="space-y-5 px-6 py-4">
			{#if !editingId}
				<div class="space-y-2">
					<Label class="text-xs">Provider</Label>
					<RadioGroup.Root value={formProvider} onValueChange={setProvider} class="grid grid-cols-2 gap-2 sm:grid-cols-3">
						{#each PROVIDERS as p (p.provider)}
							{@const PIcon = p.icon}
							<Label
								class="flex cursor-pointer items-center gap-2 rounded-md border border-input bg-transparent px-3 py-2 text-sm data-[active=true]:border-primary data-[active=true]:bg-muted"
								data-active={formProvider === p.provider}
							>
								<RadioGroup.Item value={p.provider} class="sr-only" />
								<PIcon class="size-4 shrink-0 text-muted-foreground" />
								<span class="truncate">{p.name}</span>
							</Label>
						{/each}
					</RadioGroup.Root>
				</div>
			{:else}
				{@const FIcon = formMeta.icon}
				<div class="space-y-1.5">
					<Label class="text-xs">Provider</Label>
					<div class="flex items-center gap-2 rounded-md border border-input bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
						<FIcon class="size-4 shrink-0" />
						<span class="truncate">{formMeta.name}</span>
					</div>
					<p class="text-xs text-muted-foreground">Provider can't be changed after creation — remove and re-add to switch.</p>
				</div>
			{/if}

			<div class="space-y-1.5">
				<Label class="text-xs" for="channel-name">Name</Label>
				<Input
					id="channel-name"
					bind:value={formName}
					placeholder="{formMeta.name} alerts"
					class="h-9"
					disabled={saving}
					aria-invalid={!!nameError}
					oninput={() => { if (nameError) nameError = ''; }}
				/>
				{#if nameError}<p class="text-xs text-destructive">{nameError}</p>{/if}
			</div>

			<div class="space-y-3">
				{#if formMeta.help}
					<a href={formMeta.help.url} target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 text-xs text-primary hover:underline">
						{formMeta.help.label}<ExternalLinkIcon class="size-3" />
					</a>
				{/if}
				{#each formMeta.fields as field (field.key)}
					{#if field.kind === 'bool'}
						<div class="flex items-center justify-between rounded-md border px-3 py-2">
							<Label class="text-xs">{field.label}</Label>
							<Switch
								checked={formConfig[field.key] === undefined ? !!field.default : !!formConfig[field.key]}
								onCheckedChange={(v) => setField(field.key, v)}
								disabled={saving}
							/>
						</div>
					{:else}
						<div class="space-y-1.5">
							<Label class="text-xs" for="channel-{field.key}">{field.label}</Label>
							<Input
								id="channel-{field.key}"
								type={field.kind === 'secret' && !editingId ? 'password' : field.kind === 'number' ? 'number' : 'text'}
								value={formConfig[field.key] === undefined ? '' : String(formConfig[field.key])}
								placeholder={field.kind === 'secret' && editingId && formMasked[field.key]
									? 'Leave blank to keep current'
									: (field.placeholder ?? '')}
								autocomplete="off"
								class="h-9 font-mono text-xs"
								disabled={saving}
								aria-invalid={!!fieldErrors[field.key]}
								oninput={(e) => setField(field.key, e.currentTarget.value)}
							/>
							{#if fieldErrors[field.key]}
								<p class="text-xs text-destructive">{fieldErrors[field.key]}</p>
							{:else if field.kind === 'secret' && editingId && formMasked[field.key]}
								<p class="text-xs text-muted-foreground">Stored — leave blank to keep, or type to replace.</p>
							{/if}
						</div>
					{/if}
				{/each}
			</div>

			<Separator />

			<div class="space-y-2">
				<Label class="text-xs">Notify me about</Label>
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					{#each NOTIF_CATEGORIES as cat (cat.value)}
						<Label
							class="flex cursor-pointer items-start gap-2 rounded-md border border-input px-2.5 py-2 text-xs data-[active=true]:border-primary data-[active=true]:bg-muted"
							data-active={formPref.types.includes(cat.value)}
						>
							<Checkbox
								checked={formPref.types.includes(cat.value)}
								onCheckedChange={(v) => toggleCategory(cat.value, v === true)}
								class="mt-0.5"
							/>
							<span class="min-w-0">
								<span class="block font-medium">{cat.label}</span>
								<span class="block text-muted-foreground">{cat.hint}</span>
							</span>
						</Label>
					{/each}
				</div>
				{#if categoryError}<p class="text-xs text-destructive">{categoryError}</p>{/if}
			</div>

			<div class="space-y-1.5">
				<Label class="text-xs">Minimum severity</Label>
				<Select.Root type="single" value={formPref.min_severity} onValueChange={(v) => (formPref = { ...formPref, min_severity: v ?? 'info' })}>
					<Select.Trigger class="h-9 w-full text-sm">{severityLabel}</Select.Trigger>
					<Select.Content>
						{#each NOTIF_SEVERITIES as s (s.value)}
							<Select.Item value={s.value} label={s.label}>{s.label}</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			</div>

			<div class="flex items-center justify-between rounded-lg border px-4 py-3">
				<div class="space-y-0.5">
					<Label class="text-sm font-medium">Active</Label>
					<p class="text-xs text-muted-foreground">Disabled channels keep their config but send nothing.</p>
				</div>
				<Switch checked={formActive} onCheckedChange={(v) => (formActive = v)} disabled={saving} />
			</div>
		</div>
		</ScrollArea>

		<Dialog.Footer class="border-t px-6 py-4">
			<Button variant="outline" onclick={() => (dialogOpen = false)} disabled={saving}>Cancel</Button>
			<Button onclick={handleSave} disabled={saving}>
				{#if saving}
					<Spinner class="mr-2" />
					Saving...
				{:else}
					{editingId ? 'Save changes' : 'Add channel'}
				{/if}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<Dialog.Root bind:open={deleteOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Remove channel</Dialog.Title>
			<Dialog.Description>
				Are you sure you want to remove {deletingChannel?.name ?? 'this channel'}? Notifications to it
				will stop immediately.
			</Dialog.Description>
		</Dialog.Header>
		<Dialog.Footer>
			<Button variant="outline" onclick={() => (deleteOpen = false)} disabled={isDeleting}>Cancel</Button>
			<Button variant="destructive" onclick={handleDelete} disabled={isDeleting}>
				{#if isDeleting}
					<Spinner class="mr-2" />
					Removing...
				{:else}
					Remove channel
				{/if}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
