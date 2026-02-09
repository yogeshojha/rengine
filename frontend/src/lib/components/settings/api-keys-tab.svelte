<script lang="ts">
	import { onMount } from 'svelte';
	import { apiKeysApi } from '$lib/api/api-keys';
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
	import EyeIcon from '@lucide/svelte/icons/eye';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import CheckIcon from '@lucide/svelte/icons/check';
	import PackageIcon from '@lucide/svelte/icons/package';
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
	let configuredKeys = $state<Map<string, APIKeyRead>>(new Map());
	let isLoading = $state(true);

	let addDialogOpen = $state(false);
	let addDialogProvider = $state<APIProvider | null>(null);
	let addDialogKeyValue = $state('');
	let addDialogSaving = $state(false);
	let addShowKey = $state(false);

	let editKeyValue = $state('');
	let editSaving = $state(false);
	let editShowKey = $state(false);

	let revealedKeyValue = $state<string | null>(null);
	let revealLoading = $state(false);
	let copiedKeyId = $state<string | null>(null);

	let deleteDialogOpen = $state(false);
	let deletingProvider = $state<APIProvider | null>(null);
	let deletingKeyId = $state<string | null>(null);
	let isDeleting = $state(false);

	let testingKeyId = $state<string | null>(null);

	let editPopoverOpen = $state(false);

	let testDialogOpen = $state(false);
	let testDialogKeyId = $state<string | null>(null);
	let testDialogProvider = $state<APIProvider | null>(null);

	async function fetchData() {
		isLoading = true;
		try {
			const [providerList, keyList] = await Promise.all([
				apiKeysApi.listProviders(),
				apiKeysApi.list()
			]);
			providers = providerList;
			configuredKeys = new Map(keyList.map((k) => [k.provider, k]));
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to load API keys');
		} finally {
			isLoading = false;
		}
	}

	function openAddDialog(provider: APIProvider) {
		addDialogProvider = provider;
		addDialogKeyValue = '';
		addShowKey = false;
		addDialogOpen = true;
	}

	async function handleAdd() {
		if (!addDialogProvider || !addDialogKeyValue.trim()) {
			toast.error('API key is required');
			return;
		}

		addDialogSaving = true;
		try {
			const created = await apiKeysApi.create({
				provider: addDialogProvider,
				key_value: addDialogKeyValue.trim()
			});
			configuredKeys.set(created.provider, created);
			configuredKeys = new Map(configuredKeys);
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

		editSaving = true;
		try {
			const updated = await apiKeysApi.update(key.id, {
				key_value: editKeyValue.trim()
			});
			configuredKeys.set(updated.provider, updated);
			configuredKeys = new Map(configuredKeys);
			toast.success('API key updated');
			editKeyValue = '';
			editPopoverOpen = false;
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
			configuredKeys = new Map(configuredKeys);
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
			configuredKeys = new Map(configuredKeys);
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
		revealLoading = true;
		try {
			const result = await apiKeysApi.reveal(keyId);
			revealedKeyValue = result.key_value;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to reveal key');
		} finally {
			revealLoading = false;
		}
	}

	async function copyToClipboard(keyId: string, value: string) {
		try {
			await navigator.clipboard.writeText(value);
			copiedKeyId = keyId;
			setTimeout(() => (copiedKeyId = null), 2000);
		} catch {
			toast.error('Failed to copy');
		}
	}

	function resetReveal() {
		revealedKeyValue = null;
		revealLoading = false;
		copiedKeyId = null;
	}

	function resetEdit() {
		editKeyValue = '';
		editSaving = false;
		editShowKey = false;
	}

	async function refreshProviders() {
		try {
			providers = await apiKeysApi.listProviders();
		} catch {
			// non-critical
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
			{#each Array(5) as _}
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
	{:else}
		<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
			{#each providers as provider (provider.provider)}
				{@const key = configuredKeys.get(provider.provider)}
				{@const Icon = getIcon(provider.icon)}
				{@const isConfigured = provider.configured}

				<Card.Root
					class="relative transition-all duration-200 {isConfigured
						? 'ring-1 ring-border'
						: 'border-dashed opacity-75 hover:opacity-100'}"
				>
					<Card.Content class="p-5">
						<div class="flex items-start justify-between gap-3">
							<div class="flex items-start gap-3 min-w-0">
								<div
									class="shrink-0 p-2.5 rounded-lg"
									style="background-color: {provider.color}15;"
								>
									<Icon class="size-5" style="color: {provider.color};" />
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
											<button
												type="button"
												class="text-muted-foreground hover:text-foreground transition-colors shrink-0"
											>
												<EyeIcon class="size-3.5" />
											</button>
										</Popover.Trigger>
										<Popover.Content class="w-80" align="start">
											<div class="space-y-3">
												<div class="flex items-center justify-between">
													<Label class="text-xs font-medium">Full API Key</Label>
													{#if revealedKeyValue}
														<button
															type="button"
															class="text-muted-foreground hover:text-foreground transition-colors"
															onclick={() => copyToClipboard(key.id, revealedKeyValue ?? '')}
														>
															{#if copiedKeyId === key.id}
																<CheckIcon class="size-3.5 text-emerald-500" />
															{:else}
																<CopyIcon class="size-3.5" />
															{/if}
														</button>
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
												{:else}
													<p class="text-xs text-muted-foreground">Failed to load key</p>
												{/if}
											</div>
										</Popover.Content>
									</Popover.Root>

									{#if key.is_enabled}
										<Badge
											variant="secondary"
											class="h-5 text-[10px] px-1.5 border-0 shrink-0"
											style="background-color: {provider.color}15; color: {provider.color};"
										>
											Active
										</Badge>
									{:else}
										<Badge
											variant="secondary"
											class="h-5 text-[10px] px-1.5 bg-amber-500/10 text-amber-600 dark:text-amber-400 border-0 shrink-0"
										>
											Disabled
										</Badge>
									{/if}
								</div>

								<div class="flex items-center gap-4 text-xs text-muted-foreground">
									<Tooltip.Root>
										<Tooltip.Trigger>
											<span class="flex items-center gap-1">
												<ActivityIcon class="size-3" />
												{key.usage_counter} calls
											</span>
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
										bind:open={editPopoverOpen}
										onOpenChange={(open) => {
											if (!open) resetEdit();
										}}
									>
										<Popover.Trigger>
											<Button variant="ghost" size="sm" class="h-7 px-2 text-xs">
												<Pencil class="size-3 mr-1" />
												Edit
											</Button>
										</Popover.Trigger>
										<Popover.Content class="w-80" align="start">
											<div class="space-y-3">
												<div>
													<h4 class="text-sm font-medium">Update API Key</h4>
													<p class="text-xs text-muted-foreground mt-0.5">
														Enter a new key for {provider.name}
													</p>
												</div>
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
														<button
															type="button"
															class="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
															onclick={() => (editShowKey = !editShowKey)}
														>
															<EyeIcon class="size-3.5" />
														</button>
													</div>
												</div>
												<Button
													size="sm"
													class="w-full h-8 text-xs"
													disabled={editSaving || !editKeyValue.trim()}
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
											<Button
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
										</Tooltip.Trigger>
										<Tooltip.Content>Test API key validity</Tooltip.Content>
									</Tooltip.Root>

									<div class="flex-1"></div>

									<Tooltip.Root>
										<Tooltip.Trigger>
											<Button
												variant="ghost"
												size="sm"
												class="h-7 px-2 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
												onclick={() => openDeleteDialog(provider.provider)}
											>
												<Trash2Icon class="size-3" />
											</Button>
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

<!-- Add Key Dialog -->
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

		<div class="space-y-4 py-2">
			<div class="space-y-2">
				<Label for="add-key-input">API Key</Label>
				<div class="relative">
					<Input
						id="add-key-input"
						type={addShowKey ? 'text' : 'password'}
						bind:value={addDialogKeyValue}
						placeholder="Paste your API key here"
						disabled={addDialogSaving}
						class="pr-10"
					/>
					<button
						type="button"
						class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
						onclick={() => (addShowKey = !addShowKey)}
					>
						<EyeIcon class="size-4" />
					</button>
				</div>
			</div>
		</div>

		<Dialog.Footer>
			<Button variant="outline" onclick={() => (addDialogOpen = false)} disabled={addDialogSaving}>
				Cancel
			</Button>
			<Button onclick={handleAdd} disabled={addDialogSaving || !addDialogKeyValue.trim()}>
				{#if addDialogSaving}
					<Spinner class="mr-2" />
					Saving...
				{:else}
					Add Key
				{/if}
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<!-- Delete Confirmation Dialog -->
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

<!-- test confirmation dialog -->

<Dialog.Root bind:open={testDialogOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Test API Key</Dialog.Title>
			<Dialog.Description>
				This will make a live API call to verify the key works. It will consume 1 API call from your
				ViewDNS quota.
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
