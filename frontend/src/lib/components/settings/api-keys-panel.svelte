<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { SvelteMap } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import RotateCwIcon from '@lucide/svelte/icons/rotate-cw';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { apiKeysApi } from '$lib/api/api-keys';
	import { auth } from '$lib/stores/auth.svelte';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { providerAllowed } from '$lib/config/capabilities';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { externalHref } from '$lib/utilities/links';
	import type { APIKeyRead, ProviderInfo } from '$lib/types/api-key';
	import { ProviderGroup } from '$lib/config/api-keys';
	import CheckStatus from './check-status.svelte';
	import { BODY_ROW, GROUP_ROW, HEAD_ROW, KEY_COL, KEY_SKELETON } from './columns';
	import { checkState, type CheckState } from './status';

	const GROUP_ORDER = Object.values(ProviderGroup);

	const STATUS_LABEL: Record<CheckState, string> = {
		ok: 'Valid',
		failed: 'Rejected',
		untested: 'Not tested',
		off: 'Disabled'
	};

	let providers = $state<ProviderInfo[]>([]);
	const keys = new SvelteMap<string, APIKeyRead>();
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let testing = $state<string | null>(null);

	let editing = $state<ProviderInfo | null>(null);
	let dialogOpen = $state(false);
	let keyValue = $state('');
	let username = $state('');
	let initialUsername = $state('');
	let showKey = $state(false);
	let saving = $state(false);
	let usernameInput = $state<HTMLInputElement | null>(null);
	let keyInput = $state<HTMLInputElement | null>(null);

	let removing = $state<ProviderInfo | null>(null);
	let deleting = $state(false);

	let revealed = $state<string | null>(null);
	let revealFailed = $state(false);
	let copied = $state(false);

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const replacing = $derived(editing ? keys.has(editing.provider) : false);
	const canSave = $derived(
		!saving && !!keyValue.trim() && (!editing?.requires_username || !!username.trim() || replacing)
	);
	const groups = $derived.by(() => {
		const out: { group: string; label: string; items: ProviderInfo[] }[] = [];
		for (const provider of providers) {
			let entry = out.find((g) => g.group === provider.group);
			if (!entry) {
				entry = { group: provider.group, label: provider.group_label, items: [] };
				out.push(entry);
			}
			entry.items.push(provider);
		}
		return out.sort(
			(a, b) =>
				GROUP_ORDER.indexOf(a.group as ProviderGroup) -
				GROUP_ORDER.indexOf(b.group as ProviderGroup)
		);
	});
	const setCount = $derived(providers.filter((p) => keys.has(p.provider)).length);
	const dirty = $derived(!!keyValue.trim() || username.trim() !== initialUsername);
	const guard = new DiscardGuard(
		() => dirty,
		() => (dialogOpen = false)
	);

	async function load() {
		loading = true;
		loadError = null;
		try {
			const [providerList, keyList] = await Promise.all([
				apiKeysApi.listProviders(),
				apiKeysApi.list()
			]);
			providers = providerList.filter((p) => providerAllowed(capabilitiesStore.mode, p.provider));
			keys.clear();
			for (const key of keyList) keys.set(key.provider, key);
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'API keys not loaded';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		if (isAdmin) void load();
		else loading = false;
	});

	function stateOf(provider: ProviderInfo): CheckState {
		const key = keys.get(provider.provider);
		if (!key) return 'off';
		return checkState(key.is_enabled, key.last_test_ok);
	}

	async function openDialog(provider: ProviderInfo) {
		editing = provider;
		keyValue = '';
		username = String(keys.get(provider.provider)?.key_meta?.username ?? '');
		initialUsername = username.trim();
		showKey = false;
		dialogOpen = true;
		await tick();
		(provider.requires_username && !username ? usernameInput : keyInput)?.focus();
	}

	async function saveKey() {
		const provider = editing;
		if (!provider || !canSave) return;
		saving = true;
		const name = username.trim();
		const meta = provider.requires_username && name ? { key_meta: { username: name } } : {};
		try {
			const existing = keys.get(provider.provider);
			const stored = existing
				? await apiKeysApi.update(existing.id, { key_value: keyValue.trim(), ...meta })
				: await apiKeysApi.create({
						provider: provider.provider,
						key_value: keyValue.trim(),
						...meta
					});
			keys.set(stored.provider, stored);
			toast.success(`${provider.name} key ${existing ? 'replaced' : 'added'}`);
			dialogOpen = false;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : `${provider.name} key not saved`);
		} finally {
			saving = false;
		}
	}

	async function test(provider: ProviderInfo) {
		const key = keys.get(provider.provider);
		if (!key) return;
		testing = provider.provider;
		try {
			const result = await apiKeysApi.test(key.id);
			keys.set(provider.provider, {
				...key,
				last_test_at: new Date().toISOString(),
				last_test_ok: result.success,
				last_test_message: result.message
			});
			if (result.success) toast.success(result.message);
			else toast.error(result.message);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Key not tested');
		} finally {
			testing = null;
		}
	}

	async function setEnabled(provider: ProviderInfo, enabled: boolean) {
		const key = keys.get(provider.provider);
		if (!key) return;
		try {
			keys.set(provider.provider, await apiKeysApi.update(key.id, { is_enabled: enabled }));
			toast.success(`${provider.name} key ${enabled ? 'enabled' : 'disabled'}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Key not updated');
		}
	}

	async function remove() {
		const provider = removing;
		const key = provider ? keys.get(provider.provider) : undefined;
		if (!provider || !key) return;
		deleting = true;
		try {
			await apiKeysApi.delete(key.id);
			keys.delete(provider.provider);
			toast.success(`${provider.name} key removed`);
			removing = null;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Key not removed');
		} finally {
			deleting = false;
		}
	}

	async function reveal(key: APIKeyRead) {
		revealed = null;
		revealFailed = false;
		try {
			revealed = (await apiKeysApi.reveal(key.id)).key_value;
		} catch {
			revealFailed = true;
		}
	}

	async function copy() {
		if (revealed && (await writeClipboard(revealed))) {
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} else {
			toast.error('Key not copied');
		}
	}
</script>

{#if !isAdmin}
	<EmptyState compact icon={KeyRoundIcon} title="API keys are managed by administrators" />
{:else if loading}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<div class="@container/keys w-full">
			<TableSkeleton lead={KEY_SKELETON} rows={4} actions={false} />
		</div>
	</Card.Root>
{:else if loadError}
	<EmptyState compact icon={TriangleAlertIcon} title="API keys not loaded" description={loadError}>
		<Button variant="outline" size="sm" onclick={load}>
			<RotateCwIcon class="size-3.5" />
			Retry
		</Button>
	</EmptyState>
{:else}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<div class="@container/keys w-full" role="table" aria-label="API keys">
			<div class={HEAD_ROW} role="row">
				<div class={KEY_COL.provider} role="columnheader">Provider</div>
				<div class={KEY_COL.key} role="columnheader">Key</div>
				<div class={KEY_COL.status} role="columnheader">Status</div>
				<div class={KEY_COL.tested} role="columnheader">Last tested</div>
				<div class="{KEY_COL.actions} normal-case tracking-normal tabular-nums" role="columnheader">
					{setCount} of {providers.length} set
				</div>
			</div>
			{#each groups as group (group.group)}
				<div class={GROUP_ROW} role="row">
					<div role="cell" aria-colspan={5}>{group.label}</div>
				</div>
				{#each group.items as provider (provider.provider)}
					{@const key = keys.get(provider.provider)}
					{@const check = stateOf(provider)}
					<div class={BODY_ROW} role="row">
						<div class="{KEY_COL.provider} flex flex-col" role="cell">
							<span class="flex items-center gap-1.5 text-sm leading-5 font-medium">
								{provider.name}
								<a
									href={externalHref(provider.docs_url)}
									target="_blank"
									rel="noopener noreferrer"
									class="text-muted-foreground transition-colors hover:text-foreground"
									aria-label="{provider.name} documentation"
								>
									<ExternalLinkIcon class="size-3" />
								</a>
							</span>
							<span class="text-2xs text-muted-foreground">{provider.description}</span>
						</div>
						<div class={KEY_COL.key} role="cell">
							{#if key}
								<div class="flex items-center gap-1">
									<span class="flex min-w-0 flex-col">
										<code
											class="truncate font-mono text-xs text-muted-foreground"
											title={key.key_value_masked}
										>
											{key.key_value_masked}
										</code>
										{#if key.key_meta?.username}
											<code
												class="truncate font-mono text-2xs text-muted-foreground"
												title={String(key.key_meta.username)}
											>
												{key.key_meta.username}
											</code>
										{/if}
									</span>
									<Popover.Root
										onOpenChange={(open) => {
											if (open) void reveal(key);
											else revealed = null;
										}}
									>
										<Popover.Trigger>
											{#snippet child({ props })}
												<Button
													{...props}
													variant="ghost"
													size="icon"
													class="size-7 text-muted-foreground"
													aria-label="Reveal {provider.name} key"
												>
													<EyeIcon class="size-3.5" />
												</Button>
											{/snippet}
										</Popover.Trigger>
										<Popover.Content class="w-80" align="start">
											{#if revealed}
												<div class="flex items-start gap-2">
													<code
														class="min-w-0 flex-1 rounded-md bg-muted px-2.5 py-2 font-mono text-xs break-all select-all"
													>
														{revealed}
													</code>
													<Button
														variant="ghost"
														size="icon"
														class="size-7 shrink-0"
														aria-label="Copy key"
														onclick={copy}
													>
														{#if copied}<CheckIcon class="size-3.5" />{:else}<CopyIcon
																class="size-3.5"
															/>{/if}
													</Button>
												</div>
											{:else if revealFailed}
												<p class="text-xs text-muted-foreground">Key not loaded.</p>
											{:else}
												<Skeleton class="h-8 w-full" />
											{/if}
										</Popover.Content>
									</Popover.Root>
								</div>
							{:else}
								<span class="text-xs text-muted-foreground">Not set</span>
							{/if}
						</div>
						<div class={KEY_COL.status} role="cell">
							{#if key}
								<CheckStatus
									{check}
									label={STATUS_LABEL[check]}
									message={check === 'failed' ? key.last_test_message : null}
									busy={testing === provider.provider}
									busyLabel="Testing"
									muted={check !== 'ok' && check !== 'failed'}
								/>
							{:else}
								<CheckStatus check="off" label="Not set" muted />
							{/if}
						</div>
						<div class="{KEY_COL.tested} text-xs text-muted-foreground tabular-nums" role="cell">
							{key?.last_test_at ? relativeTime(key.last_test_at) : 'Never'}
						</div>
						<div class={KEY_COL.actions} role="cell">
							{#if key}
								<DropdownMenu.Root>
									<DropdownMenu.Trigger>
										{#snippet child({ props })}
											<Button
												{...props}
												variant="ghost"
												size="icon"
												class="size-7"
												aria-label="{provider.name} key actions"
											>
												<EllipsisIcon class="size-4" />
											</Button>
										{/snippet}
									</DropdownMenu.Trigger>
									<DropdownMenu.Content align="end">
										{#if provider.testable}
											<DropdownMenu.Item
												disabled={testing !== null || !key.is_enabled}
												onSelect={() => test(provider)}
											>
												Test
											</DropdownMenu.Item>
										{/if}
										<DropdownMenu.Item onSelect={() => openDialog(provider)}>
											Replace key
										</DropdownMenu.Item>
										<DropdownMenu.Item onSelect={() => setEnabled(provider, !key.is_enabled)}>
											{key.is_enabled ? 'Disable' : 'Enable'}
										</DropdownMenu.Item>
										<DropdownMenu.Separator />
										<DropdownMenu.Item variant="destructive" onSelect={() => (removing = provider)}>
											Remove
										</DropdownMenu.Item>
									</DropdownMenu.Content>
								</DropdownMenu.Root>
							{:else}
								<Button
									variant="outline"
									size="sm"
									class="h-7"
									onclick={() => openDialog(provider)}
								>
									Add key
								</Button>
							{/if}
						</div>
					</div>
				{/each}
			{/each}
		</div>
	</Card.Root>
{/if}

<Dialog.Root
	bind:open={() => dialogOpen, (next) => (next ? (dialogOpen = true) : !saving && guard.close())}
>
	<Dialog.Content class="grid-cols-[minmax(0,1fr)] gap-0 p-0 sm:max-w-md">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>
				{editing ? `${replacing ? 'Replace' : 'Add'} ${editing.name} key` : 'API key'}
			</Dialog.Title>
			{#if editing}
				<Dialog.Description>
					<a
						href={externalHref(editing.docs_url)}
						target="_blank"
						rel="noopener noreferrer"
						class="inline-flex items-center gap-1 text-primary transition-colors hover:text-foreground"
					>
						{editing.name} documentation <ExternalLinkIcon class="size-3" />
					</a>
				</Dialog.Description>
			{:else}
				<Dialog.Description class="sr-only">Key for an external data provider.</Dialog.Description>
			{/if}
		</Dialog.Header>
		<form
			class="flex min-w-0 flex-col"
			onsubmit={(e) => {
				e.preventDefault();
				void saveKey();
			}}
		>
			<div class="flex flex-col gap-4 px-6 py-5">
				{#if editing?.requires_username}
					<FormField label="Username" required>
						{#snippet children({ id })}
							<Input
								{id}
								bind:ref={usernameInput}
								bind:value={username}
								autocomplete="off"
								disabled={saving}
							/>
						{/snippet}
					</FormField>
				{/if}
				<FormField label="API key" required>
					{#snippet children({ id })}
						<div class="relative">
							<Input
								{id}
								type={showKey ? 'text' : 'password'}
								bind:ref={keyInput}
								bind:value={keyValue}
								autocomplete="off"
								spellcheck={false}
								class="pr-10 font-mono text-xs"
								disabled={saving}
							/>
							<Button
								type="button"
								variant="ghost"
								size="icon"
								class="absolute top-1/2 right-1.5 size-7 -translate-y-1/2 text-muted-foreground"
								aria-label={showKey ? 'Hide key' : 'Show key'}
								aria-pressed={showKey}
								onclick={() => (showKey = !showKey)}
							>
								{#if showKey}<EyeOffIcon class="size-4" />{:else}<EyeIcon class="size-4" />{/if}
							</Button>
						</div>
					{/snippet}
				</FormField>
			</div>
			<Dialog.Footer class="border-t px-6 py-4">
				<Button type="button" variant="outline" disabled={saving} onclick={() => guard.close()}>
					Cancel
				</Button>
				<LoadingButton type="submit" loading={saving} loadingLabel="Saving" disabled={!canSave}>
					{replacing ? 'Replace key' : 'Add key'}
				</LoadingButton>
			</Dialog.Footer>
		</form>
	</Dialog.Content>
</Dialog.Root>

<ConfirmDialog
	open={removing !== null}
	title="Remove API key"
	description={removing ? `The ${removing.name} key is removed.` : ''}
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
