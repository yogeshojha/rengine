<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { apiKeysApi } from '$lib/api/api-keys';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { providerAllowed } from '$lib/config/capabilities';
	import { APIProvider, type APIKeyRead, type ProviderInfo } from '$lib/types/api-key';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import ApiKeyProviderCard from './api-key-provider-card.svelte';
	import { toast } from 'svelte-sonner';
	import { SvelteMap } from 'svelte/reactivity';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Empty from '$lib/components/ui/empty/index.js';

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

	let deleteDialogOpen = $state(false);
	let deletingProvider = $state<APIProvider | null>(null);
	let deletingKeyId = $state<string | null>(null);
	let isDeleting = $state(false);

	let testingKeyId = $state<string | null>(null);

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
				...(addMeta?.requires_username ? { key_meta: { username: addDialogUsername.trim() } } : {})
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

	async function handleEditSave(
		provider: APIProvider,
		keyValue: string,
		username: string
	): Promise<boolean> {
		const key = configuredKeys.get(provider);
		if (!key || !keyValue) {
			toast.error('API key is required');
			return false;
		}

		const editMeta = providers.find((p) => p.provider === provider);
		if (editMeta?.requires_username && !username) {
			toast.error('Username is required');
			return false;
		}

		try {
			const updated = await apiKeysApi.update(key.id, {
				key_value: keyValue,
				...(editMeta?.requires_username ? { key_meta: { username } } : {})
			});
			configuredKeys.set(updated.provider, updated);
			toast.success('API key updated');
			return true;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to update API key');
			return false;
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

	function openTestDialog(provider: APIProvider, keyId: string) {
		testDialogKeyId = keyId;
		testDialogProvider = provider;
		testDialogOpen = true;
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

	async function handleReveal(keyId: string): Promise<string> {
		const result = await apiKeysApi.reveal(keyId);
		return result.key_value;
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
				<Empty.Title class="text-sm font-medium text-foreground">Couldn't load API keys</Empty.Title
				>
				<Empty.Description class="mt-1 text-xs text-muted-foreground">{loadError}</Empty.Description
				>
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
				<ApiKeyProviderCard
					{provider}
					apiKey={configuredKeys.get(provider.provider)}
					testing={testingKeyId === configuredKeys.get(provider.provider)?.id}
					onToggle={handleToggle}
					onAdd={openAddDialog}
					onTest={openTestDialog}
					onDelete={openDeleteDialog}
					onReveal={handleReveal}
					onEditSave={handleEditSave}
				/>
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
				{#if addRequiresUsername}
					<FormField label="Username">
						{#snippet children({ id })}
							<Input
								{id}
								type="text"
								bind:ref={addUsernameInput}
								bind:value={addDialogUsername}
								placeholder="Account username"
								disabled={addDialogSaving}
							/>
						{/snippet}
					</FormField>
				{/if}
				<FormField label="API Key">
					{#snippet children({ id })}
						<div class="relative">
							<Input
								{id}
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
					{/snippet}
				</FormField>
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
				<LoadingButton
					type="submit"
					loading={addDialogSaving}
					loadingLabel="Saving..."
					disabled={!addCanSave}
				>
					Add Key
				</LoadingButton>
			</Dialog.Footer>
		</form>
	</Dialog.Content>
</Dialog.Root>

<DeleteConfirmationDialog
	bind:open={deleteDialogOpen}
	title="Remove API Key"
	description={deletingProvider
		? `Are you sure you want to remove the ${providers.find((p) => p.provider === deletingProvider)?.name ?? ''} API key? Any features depending on this provider will stop working.`
		: ''}
	confirmLabel="Remove Key"
	{isDeleting}
	onOpenChange={(open) => (deleteDialogOpen = open)}
	onConfirm={handleDelete}
/>

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
			<LoadingButton
				loading={testingKeyId !== null}
				loadingLabel="Testing..."
				onclick={async () => {
					if (testDialogKeyId) {
						testDialogOpen = false;
						await handleTest(testDialogKeyId);
					}
				}}
			>
				Test
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
