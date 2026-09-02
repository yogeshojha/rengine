<script lang="ts">
	import type { Component } from 'svelte';
	import { APIProvider, type APIKeyRead, type ProviderInfo } from '$lib/types/api-key';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { toast } from 'svelte-sonner';
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
	import { formatDate } from '$lib/utilities';

	interface Props {
		provider: ProviderInfo;
		apiKey: APIKeyRead | undefined;
		testing: boolean;
		onToggle: (provider: APIProvider, enabled: boolean) => void;
		onAdd: (provider: APIProvider) => void;
		onTest: (provider: APIProvider, keyId: string) => void;
		onDelete: (provider: APIProvider) => void;
		onReveal: (keyId: string) => Promise<string>;
		onEditSave: (provider: APIProvider, keyValue: string, username: string) => Promise<boolean>;
	}

	let {
		provider,
		apiKey,
		testing,
		onToggle,
		onAdd,
		onTest,
		onDelete,
		onReveal,
		onEditSave
	}: Props = $props();

	const ICON_MAP: Record<string, Component> = {
		globe: GlobeIcon,
		shield: ShieldIcon,
		radar: RadarIcon,
		route: RouteIcon,
		'scan-search': ScanSearchIcon
	};

	const Icon = $derived(ICON_MAP[provider.icon] ?? PackageIcon);
	const isConfigured = $derived(!!apiKey);

	let revealedKeyValue = $state<string | null>(null);
	let revealLoading = $state(false);
	let revealError = $state(false);
	let copied = $state(false);

	let editOpen = $state(false);
	let editKeyValue = $state('');
	let editUsername = $state('');
	let editSaving = $state(false);
	let editShowKey = $state(false);

	function resetReveal() {
		revealedKeyValue = null;
		revealLoading = false;
		revealError = false;
		copied = false;
	}

	async function reveal(keyId: string) {
		revealedKeyValue = null;
		revealError = false;
		revealLoading = true;
		try {
			revealedKeyValue = await onReveal(keyId);
		} catch {
			revealError = true;
		} finally {
			revealLoading = false;
		}
	}

	async function copyKey(value: string) {
		if (await writeClipboard(value)) {
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} else {
			toast.error('Failed to copy');
		}
	}

	function resetEdit() {
		editKeyValue = '';
		editUsername = '';
		editSaving = false;
		editShowKey = false;
	}

	async function saveEdit() {
		editSaving = true;
		try {
			if (await onEditSave(provider.provider, editKeyValue.trim(), editUsername.trim())) {
				editOpen = false;
			}
		} finally {
			editSaving = false;
		}
	}
</script>

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

			{#if apiKey}
				<Switch
					checked={apiKey.is_enabled}
					onCheckedChange={(checked) => onToggle(provider.provider, checked)}
				/>
			{/if}
		</div>

		{#if apiKey}
			<Separator class="my-3" />

			<div class="space-y-3">
				{#if provider.requires_username && apiKey.key_meta?.username}
					<div class="flex items-center gap-2">
						<UserIcon class="size-3.5 text-muted-foreground shrink-0" />
						<code class="text-xs font-mono text-muted-foreground truncate">
							{apiKey.key_meta.username}
						</code>
					</div>
				{/if}
				<div class="flex items-center gap-2">
					<KeyIcon class="size-3.5 text-muted-foreground shrink-0" />
					<code class="text-xs font-mono text-muted-foreground truncate">
						{apiKey.key_value_masked}
					</code>

					<Popover.Root
						onOpenChange={(open) => {
							if (open) reveal(apiKey.id);
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
											onclick={() => copyKey(revealedKeyValue ?? '')}
										>
											{#if copied}
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
								{:else if revealError}
									<div class="flex items-center justify-between gap-2">
										<p class="text-xs text-muted-foreground">Failed to load key</p>
										<Button
											variant="outline"
											size="sm"
											class="h-7 px-2 text-xs"
											onclick={() => reveal(apiKey.id)}
										>
											<RefreshCwIcon class="size-3 mr-1" />
											Retry
										</Button>
									</div>
								{/if}
							</div>
						</Popover.Content>
					</Popover.Root>

					{#if apiKey.is_enabled}
						<Badge variant="secondary" class="h-5 text-[10px] px-1.5 shrink-0">Active</Badge>
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
									{apiKey.usage_counter} calls
								</span>
							{/snippet}
						</Tooltip.Trigger>
						<Tooltip.Content>Total API calls made</Tooltip.Content>
					</Tooltip.Root>

					{#if apiKey.last_used_at}
						<span>Last used {formatDate(apiKey.last_used_at)}</span>
					{:else}
						<span>Never used</span>
					{/if}
				</div>

				<div class="flex items-center gap-1.5 pt-1">
					<Popover.Root
						open={editOpen}
						onOpenChange={(open) => {
							if (open) {
								editOpen = true;
								editKeyValue = '';
								editUsername = (apiKey.key_meta?.username as string) ?? '';
							} else {
								editOpen = false;
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
									<FormField label="Username">
										{#snippet children({ id })}
											<Input
												{id}
												type="text"
												bind:value={editUsername}
												placeholder="Account username"
												disabled={editSaving}
												class="h-8 text-xs"
											/>
										{/snippet}
									</FormField>
								{/if}
								<FormField label="New API Key">
									{#snippet children({ id })}
										<div class="relative">
											<Input
												{id}
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
									{/snippet}
								</FormField>
								<LoadingButton
									size="sm"
									class="w-full h-8 text-xs"
									loading={editSaving}
									loadingLabel="Saving…"
									disabled={!editKeyValue.trim() ||
										(provider.requires_username && !editUsername.trim())}
									onclick={saveEdit}
								>
									Update Key
								</LoadingButton>
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
									disabled={testing}
									onclick={() => onTest(provider.provider, apiKey.id)}
								>
									{#if testing}
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
									onclick={() => onDelete(provider.provider)}
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
					onclick={() => onAdd(provider.provider)}
				>
					<PlusIcon class="size-3.5 mr-1.5" />
					Add API key
				</Button>
			</div>
		{/if}
	</Card.Content>
</Card.Root>
