<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { apiKeysApi } from '$lib/api/api-keys';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { providerAllowed } from '$lib/config/capabilities';
	import { APIProvider, type APIKeyRead, type ProviderInfo } from '$lib/types/api-key';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { toast } from 'svelte-sonner';
	import { SvelteMap } from 'svelte/reactivity';
	import type { Component } from 'svelte';
	import GlobeIcon from '@lucide/svelte/icons/globe';
	import ShieldIcon from '@lucide/svelte/icons/shield';
	import RadarIcon from '@lucide/svelte/icons/radar';
	import RouteIcon from '@lucide/svelte/icons/route';
	import ScanSearchIcon from '@lucide/svelte/icons/scan-search';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import ActivityIcon from '@lucide/svelte/icons/activity';
	import KeyIcon from '@lucide/svelte/icons/key';
	import UserIcon from '@lucide/svelte/icons/user';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import CheckIcon from '@lucide/svelte/icons/check';
	import PackageIcon from '@lucide/svelte/icons/package';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import { formatDate } from '$lib/utilities';

	const ICON_MAP: Record<string, Component> = {
		globe: GlobeIcon,
		shield: ShieldIcon,
		radar: RadarIcon,
		route: RouteIcon,
		'scan-search': ScanSearchIcon
	};

	function getIcon(iconName: string): Component {
		return ICON_MAP[iconName] ?? PackageIcon;
	}

	let providers = $state<ProviderInfo[]>([]);
	let configuredKeys = new SvelteMap<string, APIKeyRead>();
	let isLoading = $state(true);
	let loadError = $state<string | null>(null);

	let addDialogOpen = $state(false);
	let addDialogProvider = $state<APIProvider | null>(null);
	let addDialogKeyValue = $state('');
	let addDialogUsername = $state('');
	let addDialogSaving = $state(false);
	let addShowKey = $state(false);
	let addUsernameInput = $state<HTMLInputElement | null>(null);
	let addKeyInput = $state<HTMLInputElement | null>(null);

	$effect(() => {
		if (addDialogOpen) {
			tick().then(() => (addUsernameInput ?? addKeyInput)?.focus());
		}
	});

	let addRequiresUsername = $derived(
		!!providers.find((p) => p.provider === addDialogProvider)?.requires_username
	);
	let addCanSave = $derived(
		!addDialogSaving &&
			!!addDialogKeyValue.trim() &&
			(!addRequiresUsername || !!addDialogUsername.trim())
	);

	let editKeyValue = $state('');
	let editUsername = $state('');
	let editSaving = $state(false);
	let editShowKey = $state(false);

	let revealedKeyValue = $state<string | null>(null);
	let revealLoading = $state(false);
	let revealError = $state(false);
	let revealKeyId = $state<string | null>(null);
	let copiedKeyId = $state<string | null>(null);

	let deleteDialogOpen = $state(false);
	let deletingProvider = $state<APIProvider | null>(null);
	let deletingKeyId = $state<string | null>(null);
	let isDeleting = $state(false);

	let testingKeyId = $state<string | null>(null);

	let editOpenId = $state<string | null>(null);

	let testDialogOpen = $state(false);
	let testDialogKeyId = $state<string | null>(null);
	let testDialogProvider = $state<APIProvider | null>(null);

	async function fetchData() {
		isLoading = true;
		loadError = null;
		try {
			const [providerList, keyList] = await Promise.all([
				apiKeysApi.listProviders(),
				apiKeysApi.list()
			]);
			providers = providerList.filter((p) => providerAllowed(capabilitiesStore.mode, p.provider));
			configuredKeys.clear();
			for (const k of keyList) configuredKeys.set(k.provider, k);
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Failed to load API keys';
			toast.error(loadError);
		} finally {
			isLoading = false;
		}
	}

	function openAddDialog(provider: APIProvider) {
		addDialogProvider = provider;
		addDialogKeyValue = '';
		addDialogUsername = '';
		addShowKey = false;
		addDialogOpen = true;
	}

	async function handleAdd() {
		if (!addDialogProvider || !addDialogKeyValue.trim()) {
			toast.error('API key is required');
			return;
		}

		const addMeta = providers.find((p) => p.provider === addDialogProvider);
		if (addMeta?.requires_username && !addDialogUsername.trim()) {
			toast.error('Username is required');
			return;
		}

		addDialogSaving = true;
		try {
			const created = await apiKeysApi.create({
				provider: addDialogProvider,
				key_value: addDialogKeyValue.trim(),
				...(addMeta?.requires_username
					? { key_meta: { username: addDialogUsername.trim() } }
					: {})
			});
			configuredKeys.set(created.provider, created);
			const meta = providers.find((p) => p.provider === addDialogProvider);
			toast.success(`${meta?.name ?? 'Provider'} API key added`);
			await refreshProviders();
			addDialogOpen = false;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to add API key');
		} finally {
			addDialogSaving = false;
		}
	}

	async function handleEditSave(provider: APIProvider) {
		const key = configuredKeys.get(provider);
		if (!key || !editKeyValue.trim()) {
			toast.error('API key is required');
			return;
		}

		const editMeta = providers.find((p) => p.provider === provider);
		if (editMeta?.requires_username && !editUsername.trim()) {
			toast.error('Username is required');
			return;
		}

		editSaving = true;
		try {
			const updated = await apiKeysApi.update(key.id, {
				key_value: editKeyValue.trim(),
				...(editMeta?.requires_username
					? { key_meta: { username: editUsername.trim() } }
					: {})
			});
			configuredKeys.set(updated.provider, updated);
			toast.success('API key updated');
			editKeyValue = '';
			editUsername = '';
			editOpenId = null;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to update API key');
		} finally {
			editSaving = false;
		}
	}

	async function handleToggle(provider: APIProvider, enabled: boolean) {
		const key = configuredKeys.get(provider);
		if (!key) return;

		try {
			const updated = await apiKeysApi.update(key.id, { is_enabled: enabled });
			configuredKeys.set(updated.provider, updated);
			await refreshProviders();
			toast.success(`${key.meta.name} ${enabled ? 'enabled' : 'disabled'}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to update');
		}
	}

	function openDeleteDialog(provider: APIProvider) {
		const key = configuredKeys.get(provider);
		if (!key) return;
		deletingProvider = provider;
		deletingKeyId = key.id;
		deleteDialogOpen = true;
	}

	async function handleDelete() {
		if (!deletingKeyId || !deletingProvider) return;

		isDeleting = true;
		try {
			await apiKeysApi.delete(deletingKeyId);
			configuredKeys.delete(deletingProvider);
			await refreshProviders();
			toast.success('API key removed');
			deleteDialogOpen = false;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to delete');
		} finally {
			isDeleting = false;
		}
	}

	async function handleTest(keyId: string) {
		testingKeyId = keyId;
		try {
			const result = await apiKeysApi.test(keyId);
			if (result.success) {
				toast.success(result.message);
			} else {
				toast.error(result.message);
			}
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Test failed');
		} finally {
			testingKeyId = null;
		}
	}

	async function handleReveal(keyId: string) {
		revealedKeyValue = null;
		revealError = false;
		revealKeyId = keyId;
		revealLoading = true;
		try {
			const result = await apiKeysApi.reveal(keyId);
			revealedKeyValue = result.key_value;
		} catch {
			revealError = true;
		} finally {
			revealLoading = false;
		}
	}

	async function writeClipboard(text: string): Promise<boolean> {
		if (navigator.clipboard && window.isSecureContext) {
			try {
				await navigator.clipboard.writeText(text);
				return true;
			} catch {
				/* empty */
			}
		}
		try {
			const ta = document.createElement('textarea');
			ta.value = text;
			ta.style.position = 'fixed';
			ta.style.opacity = '0';
			document.body.appendChild(ta);
			ta.focus();
			ta.select();
			const ok = document.execCommand('copy');
			ta.remove();
			return ok;
		} catch {
			return false;
		}
	}

	async function copyToClipboard(keyId: string, value: string) {
		if (await writeClipboard(value)) {
			copiedKeyId = keyId;
			setTimeout(() => (copiedKeyId = null), 2000);
		} else {
			toast.error('Failed to copy');
		}
	}

	function resetReveal() {
		revealedKeyValue = null;
		revealLoading = false;
		revealError = false;
		revealKeyId = null;
		copiedKeyId = null;
	}

	function resetEdit() {
		editKeyValue = '';
		editUsername = '';
		editSaving = false;
		editShowKey = false;
	}

	async function refreshProviders() {
		try {
			providers = (await apiKeysApi.listProviders()).filter((p) =>
				providerAllowed(capabilitiesStore.mode, p.provider)
			);
		} catch {
			/* empty */
		}
	}

	onMount(() => {
		fetchData();
	});
</script>

<div class="space-y-6">
	<div class="flex items-start justify-between">
		<div>
			<h3 class="text-lg font-semibold">API Keys</h3>
			<p class="text-sm text-muted-foreground">
				Configure API keys for external intelligence providers. Keys are used instance-wide across
				all projects.
			</p>
		</div>
		<Badge variant="outline" class="text-xs">
			{configuredKeys.size} / {providers.length} configured
		</Badge>
	</div>

	<Separator />

	{#if isLoading}
		<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
			{#each Array(6) as _, i (i)}
				<Card.Root>
					<Card.Content class="p-5">
						<div class="flex items-start gap-3">
							<Skeleton class="size-10 rounded-lg" />
							<div class="flex-1 space-y-2">
								<Skeleton class="h-5 w-28" />
								<Skeleton class="h-4 w-full" />
								<Skeleton class="h-4 w-3/4" />
							</div>
						</div>
					</Card.Content>
				</Card.Root>
			{/each}
		</div>
	{:else if loadError}
		<Empty.Root class="min-h-[200px] gap-0 border border-border bg-muted/20 p-8">
			<Empty.Header class="gap-0">
				<Empty.Media class="mb-3">
					<TriangleAlertIcon class="size-6 text-muted-foreground" />
				</Empty.Media>
				<Empty.Title class="text-sm font-medium text-foreground">Couldn't load API keys</Empty.Title>
				<Empty.Description class="mt-1 text-xs text-muted-foreground">{loadError}</Empty.Description>
			</Empty.Header>
			<Empty.Content class="mt-4">
				<Button variant="outline" size="sm" onclick={fetchData}>
					<RefreshCwIcon class="size-3.5 mr-1.5" />
					Retry
				</Button>
			</Empty.Content>
		</Empty.Root>
	{:else}
		<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
			{#each providers as provider (provider.provider)}
				{@const key = configuredKeys.get(provider.provider)}
				{@const Icon = getIcon(provider.icon)}
				{@const isConfigured = !!key}

				<Card.Root
					class="relative transition-all duration-200 {isConfigured
						? 'ring-1 ring-border'
						: 'border-dashed opacity-75 hover:opacity-100'}"
				>
					<Card.Content class="p-5">
						<div class="flex items-start justify-between gap-3">
							<div class="flex items-start gap-3 min-w-0">
								<div class="shrink-0 rounded-lg border bg-muted p-2.5">
									<Icon class="size-[18px] text-muted-foreground" />
								</div>
								<div class="min-w-0">
									<div class="flex items-center gap-2">
										<h4 class="font-medium text-sm">{provider.name}</h4>
										<a
											href={provider.docs_url}
											target="_blank"
											rel="noopener noreferrer"
											class="text-muted-foreground hover:text-foreground transition-colors"
										>
											<ExternalLinkIcon class="size-3.5" />
										</a>
									</div>
									<p class="text-xs text-muted-foreground mt-0.5 line-clamp-2">
										{provider.description}
									</p>
								</div>
							</div>

							{#if isConfigured && key}
								<Switch
									checked={key.is_enabled}
									onCheckedChange={(checked) => handleToggle(provider.provider, checked)}
								/>
							{/if}
						</div>

						{#if isConfigured && key}
							<Separator class="my-3" />

							<div class="space-y-3">
								{#if provider.requires_username && key.key_meta?.username}
									<div class="flex items-center gap-2">
										<UserIcon class="size-3.5 text-muted-foreground shrink-0" />
										<code class="text-xs font-mono text-muted-foreground truncate">
											{key.key_meta.username}
										</code>
									</div>
								{/if}
								<div class="flex items-center gap-2">
									<KeyIcon class="size-3.5 text-muted-foreground shrink-0" />
									<code class="text-xs font-mono text-muted-foreground truncate">
										{key.key_value_masked}
									</code>

									<Popover.Root
										onOpenChange={(open) => {
											if (open) handleReveal(key.id);
											else resetReveal();
										}}
									>
										<Popover.Trigger>
											{#snippet child({ props })}
												<Button
													{...props}
													variant="ghost"
													size="icon"
													class="size-7 shrink-0 text-muted-foreground hover:text-foreground"
												>
													<EyeIcon class="size-3.5" />
												</Button>
											{/snippet}
										</Popover.Trigger>
										<Popover.Content class="w-80" align="start">
											<div class="space-y-3">
												<div class="flex items-center justify-between">
													<Label class="text-xs font-medium">Full API Key</Label>
													{#if revealedKeyValue}
														<Button
															variant="ghost"
															size="icon"
															class="size-7 text-muted-foreground hover:text-foreground"
															onclick={() => copyToClipboard(key.id, revealedKeyValue ?? '')}
														>
															{#if copiedKeyId === key.id}
																<CheckIcon class="size-3.5 text-foreground" />
															{:else}
																<CopyIcon class="size-3.5" />
															{/if}
														</Button>
													{/if}
												</div>
												{#if revealLoading}
													<div class="flex items-center justify-center py-3">
														<Spinner class="size-4" />
													</div>
												{:else if revealedKeyValue}
													<code
														class="block text-xs font-mono text-foreground bg-muted px-3 py-2.5 rounded-md break-all select-all leading-relaxed"
													>
														{revealedKeyValue}
													</code>
												{:else if revealError && revealKeyId === key.id}
													<div class="flex items-center justify-between gap-2">
														<p class="text-xs text-muted-foreground">Failed to load key</p>
														<Button
															variant="outline"
															size="sm"
															class="h-7 px-2 text-xs"
															onclick={() => handleReveal(key.id)}
														>
															<RefreshCwIcon class="size-3 mr-1" />
															Retry
														</Button>
													</div>
												{/if}
											</div>
										</Popover.Content>
									</Popover.Root>

									{#if key.is_enabled}
										<Badge
											variant="secondary"
											class="h-5 text-[10px] px-1.5 shrink-0"
										>
											Active
										</Badge>
									{:else}
										<Badge
											variant="secondary"
											class="h-5 text-[10px] px-1.5 bg-muted text-muted-foreground border-0 shrink-0"
										>
											Disabled
										</Badge>
									{/if}
								</div>

								<div class="flex items-center gap-4 text-xs text-muted-foreground">
									<Tooltip.Root>
										<Tooltip.Trigger>
											{#snippet child({ props })}
												<span {...props} class="flex items-center gap-1">
													<ActivityIcon class="size-3" />
													{key.usage_counter} calls
												</span>
											{/snippet}
										</Tooltip.Trigger>
										<Tooltip.Content>Total API calls made</Tooltip.Content>
									</Tooltip.Root>

									{#if key.last_used_at}
										<span>Last used {formatDate(key.last_used_at)}</span>
									{:else}
										<span>Never used</span>
									{/if}
								</div>

								<div class="flex items-center gap-1.5 pt-1">
									<Popover.Root
										open={editOpenId === key.id}
										onOpenChange={(open) => {
											if (open) {
												editOpenId = key.id;
												editKeyValue = '';
												editUsername = (key.key_meta?.username as string) ?? '';
											} else {
												editOpenId = null;
												resetEdit();
											}
										}}
									>
										<Popover.Trigger>
											{#snippet child({ props })}
												<Button {...props} variant="ghost" size="sm" class="h-7 px-2 text-xs">
													<Pencil class="size-3 mr-1" />
													Edit
												</Button>
											{/snippet}
										</Popover.Trigger>
										<Popover.Content class="w-80" align="start">
											<div class="space-y-3">
												<div>
													<h4 class="text-sm font-medium">Update API Key</h4>
													<p class="text-xs text-muted-foreground mt-0.5">
														Enter a new key for {provider.name}
													</p>
												</div>
												{#if provider.requires_username}
													<div class="space-y-2">
														<Label for="edit-username-{key.id}" class="text-xs">Username</Label>
														<Input
															id="edit-username-{key.id}"
															type="text"
															bind:value={editUsername}
															placeholder="Account username"
															disabled={editSaving}
															class="h-8 text-xs"
														/>
													</div>
												{/if}
												<div class="space-y-2">
													<Label for="edit-key-{key.id}" class="text-xs">New API Key</Label>
													<div class="relative">
														<Input
															id="edit-key-{key.id}"
															type={editShowKey ? 'text' : 'password'}
															bind:value={editKeyValue}
															placeholder="Paste new API key"
															disabled={editSaving}
															class="h-8 text-xs pr-8"
														/>
														<Button
															variant="ghost"
															size="icon"
															class="absolute right-1 top-1/2 size-6 -translate-y-1/2 text-muted-foreground hover:text-foreground"
															onclick={() => (editShowKey = !editShowKey)}
														>
															<EyeIcon class="size-3.5" />
														</Button>
													</div>
												</div>
												<Button
													size="sm"
													class="w-full h-8 text-xs"
													disabled={editSaving ||
														!editKeyValue.trim() ||
														(provider.requires_username && !editUsername.trim())}
													onclick={() => handleEditSave(provider.provider)}
												>
													{#if editSaving}
														<Spinner class="size-3 mr-1.5" />
														Saving...
													{:else}
														Update Key
													{/if}
												</Button>
											</div>
										</Popover.Content>
									</Popover.Root>

									<Tooltip.Root>
										<Tooltip.Trigger>
											{#snippet child({ props })}
												<Button
													{...props}
													variant="ghost"
													size="sm"
													class="h-7 px-2 text-xs"
													disabled={testingKeyId === key.id}
													onclick={() => {
														testDialogKeyId = key.id;
														testDialogProvider = provider.provider;
														testDialogOpen = true;
													}}
												>
													{#if testingKeyId === key.id}
														<Spinner class="size-3 mr-1" />
													{:else}
														<FlaskConicalIcon class="size-3 mr-1" />
													{/if}
													Test
												</Button>
											{/snippet}
										</Tooltip.Trigger>
										<Tooltip.Content>Test API key validity</Tooltip.Content>
									</Tooltip.Root>

									<div class="flex-1"></div>

									<Tooltip.Root>
										<Tooltip.Trigger>
											{#snippet child({ props })}
												<Button
													{...props}
													variant="ghost"
													size="sm"
													class="h-7 px-2 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
													onclick={() => openDeleteDialog(provider.provider)}
												>
													<Trash2Icon class="size-3" />
												</Button>
											{/snippet}
										</Tooltip.Trigger>
										<Tooltip.Content>Remove API key</Tooltip.Content>
									</Tooltip.Root>
								</div>
							</div>
						{:else}
							<div class="mt-4">
								<Button
									variant="outline"
									size="sm"
									class="w-full h-8 text-xs"
									onclick={() => openAddDialog(provider.provider)}
								>
									<PlusIcon class="size-3.5 mr-1.5" />
									Add API Key
								</Button>
							</div>
						{/if}
					</Card.Content>
				</Card.Root>
			{/each}
		</div>
	{/if}
</div>

<Dialog.Root bind:open={addDialogOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Add API Key</Dialog.Title>
			<Dialog.Description>
				{#if addDialogProvider}
					{@const meta = providers.find((p) => p.provider === addDialogProvider)}
					{#if meta}
						Configure your {meta.name} API key.
						<a
							href={meta.docs_url}
							target="_blank"
							rel="noopener noreferrer"
							class="inline-flex items-center gap-1 text-primary hover:underline ml-1"
						>
							Get a key <ExternalLinkIcon class="size-3" />
						</a>
					{/if}
				{/if}
			</Dialog.Description>
		</Dialog.Header>

		<form
			onsubmit={(e) => {
				e.preventDefault();
				if (addCanSave) handleAdd();
			}}
		>
			<div class="space-y-4 py-2">
				{#if addDialogProvider}
					{@const addMeta = providers.find((p) => p.provider === addDialogProvider)}
					{#if addMeta?.requires_username}
						<div class="space-y-2">
							<Label for="add-username-input">Username</Label>
							<Input
								id="add-username-input"
								type="text"
								bind:ref={addUsernameInput}
								bind:value={addDialogUsername}
								placeholder="Account username"
								disabled={addDialogSaving}
							/>
						</div>
					{/if}
				{/if}
				<div class="space-y-2">
					<Label for="add-key-input">API Key</Label>
					<div class="relative">
						<Input
							id="add-key-input"
							type={addShowKey ? 'text' : 'password'}
							bind:ref={addKeyInput}
							bind:value={addDialogKeyValue}
							placeholder="Paste your API key here"
							disabled={addDialogSaving}
							class="pr-10"
						/>
						<Button
							type="button"
							variant="ghost"
							size="icon"
							class="absolute right-1.5 top-1/2 size-7 -translate-y-1/2 text-muted-foreground hover:text-foreground"
							onclick={() => (addShowKey = !addShowKey)}
						>
							<EyeIcon class="size-4" />
						</Button>
					</div>
				</div>
			</div>

			<Dialog.Footer>
				<Button
					type="button"
					variant="outline"
					onclick={() => (addDialogOpen = false)}
					disabled={addDialogSaving}
				>
					Cancel
				</Button>
				<Button type="submit" disabled={!addCanSave}>
					{#if addDialogSaving}
						<Spinner class="mr-2" />
						Saving...
					{:else}
						Add Key
					{/if}
				</Button>
			</Dialog.Footer>
		</form>
	</Dialog.Content>
</Dialog.Root>

<Dialog.Root bind:open={deleteDialogOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Remove API Key</Dialog.Title>
			<Dialog.Description>
				{#if deletingProvider}
					{@const meta = providers.find((p) => p.provider === deletingProvider)}
					Are you sure you want to remove the {meta?.name ?? ''} API key? Any features depending on this
					provider will stop working.
				{/if}
			</Dialog.Description>
		</Dialog.Header>

		<Dialog.Footer>
			<Button variant="outline" onclick={() => (deleteDialogOpen = false)} disabled={isDeleting}>
				Cancel
			</Button>
			<Button variant="destructive" onclick={handleDelete} disabled={isDeleting}>
				{#if isDeleting}
					<Spinner class="mr-2" />
					Removing...
				{:else}
					Remove Key
				{/if}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<Dialog.Root bind:open={testDialogOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Test API Key</Dialog.Title>
			<Dialog.Description>
				This will make a live API call to verify the key works. It will consume 1 API call from your
				{providers.find((p) => p.provider === testDialogProvider)?.name ?? 'provider'} quota.
			</Dialog.Description>
		</Dialog.Header>
		<Dialog.Footer>
			<Button
				variant="outline"
				onclick={() => (testDialogOpen = false)}
				disabled={testingKeyId !== null}
			>
				Cancel
			</Button>
			<Button
				onclick={async () => {
					if (testDialogKeyId) {
						testDialogOpen = false;
						await handleTest(testDialogKeyId);
					}
				}}
				disabled={testingKeyId !== null}
			>
				{#if testingKeyId !== null}
					<Spinner class="mr-2" />
					Testing...
				{:else}
					Test
				{/if}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
