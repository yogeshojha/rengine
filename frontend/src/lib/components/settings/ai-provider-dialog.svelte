<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import ModelPicker from './model-picker.svelte';
	import { ai } from '$lib/stores/ai.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import { DEFAULT_AI_PROVIDER, MAX_CONNECTION_NAME, connectionName } from '$lib/config/ai';
	import type { AiConnection, AiModelsRequest, AiTestResult } from '$lib/types/ai';

	interface Props {
		open: boolean;
		connection: AiConnection | null;
	}

	let { open = $bindable(), connection }: Props = $props();

	const SERVER_URL = /^https?:\/\/[^/\s]+/i;

	let provider = $state<string>(DEFAULT_AI_PROVIDER);
	let typedName = $state('');
	let nameTouched = $state(false);
	let baseUrl = $state('');
	let apiKey = $state('');
	let showKey = $state(false);
	let workspaceId = $state('');
	let model = $state('');
	let testing = $state(false);
	let tested = $state<{ draft: string; result: AiTestResult } | null>(null);
	let initial = $state('');
	let attempted = $state(false);

	const spec = $derived(ai.provider(provider));
	const editing = $derived(connection);
	const taken = $derived(ai.connections.filter((c) => c.id !== connection?.id).map((c) => c.name));
	const suggestedName = $derived(connectionName(spec, baseUrl, taken));
	const name = $derived(nameTouched ? typedName : suggestedName);
	const serverUrl = $derived(spec?.needs_base_url ? baseUrl.trim() : '');
	const sameServer = $derived(
		!!connection &&
			connection.provider === provider &&
			(connection.base_url ?? '') === serverUrl.replace(/\/+$/, '')
	);
	const keyStored = $derived(sameServer && !!connection?.key_masked);
	const freshKey = $derived(apiKey.trim());
	const keyMissing = $derived(!!spec && !spec.key_optional && !freshKey && !keyStored);
	const workspace = $derived(spec?.workspace ? workspaceId.trim() : '');
	const draft = $derived(JSON.stringify([provider, serverUrl, freshKey, workspace, model.trim()]));
	const result = $derived(tested?.draft === draft ? tested.result : null);
	const form = $derived(
		JSON.stringify([
			provider,
			name.trim(),
			baseUrl.trim(),
			apiKey.trim(),
			workspaceId.trim(),
			model.trim()
		])
	);
	const guard = new DiscardGuard(
		() => form !== initial,
		() => (open = false)
	);

	const request = $derived.by((): AiModelsRequest | null => {
		if (!spec || keyMissing) return null;
		if (spec.needs_base_url && !SERVER_URL.test(serverUrl)) return null;
		return {
			provider,
			...(serverUrl ? { base_url: serverUrl } : {}),
			...(freshKey ? { api_key: freshKey } : {}),
			...(spec.workspace ? { workspace_id: workspace } : {}),
			...(connection && keyStored && !freshKey ? { connection_id: connection.id } : {})
		};
	});

	$effect.pre(() => {
		if (!open) return;
		untrack(() => {
			const row = connection;
			provider = row?.provider ?? DEFAULT_AI_PROVIDER;
			baseUrl = row?.base_url ?? '';
			apiKey = '';
			showKey = false;
			workspaceId = row?.workspace_id ?? '';
			model = row?.model ?? ai.provider(provider)?.default_model ?? '';
			typedName = row?.name ?? '';
			nameTouched = !!row && row.name !== connectionName(ai.provider(row.provider), baseUrl, taken);
			tested = null;
			attempted = false;
			initial = form;
		});
	});

	function pickProvider(value: string) {
		if (!value || value === provider) return;
		provider = value;
		model = ai.provider(value)?.default_model ?? '';
	}

	function rename(value: string) {
		typedName = value;
		nameTouched = true;
	}

	type Field = 'provider' | 'url' | 'key' | 'model';

	function missing(): { field: Field; message: string } | null {
		if (!spec) return { field: 'provider', message: 'Choose a provider' };
		if (spec.needs_base_url && !serverUrl)
			return { field: 'url', message: 'Server URL is required' };
		if (keyMissing) return { field: 'key', message: 'API key is required' };
		if (!model.trim()) return { field: 'model', message: 'Choose a model' };
		return null;
	}

	const problem = $derived(attempted ? missing() : null);

	function errorFor(field: Field): string | undefined {
		return problem?.field === field ? problem.message : undefined;
	}

	async function test() {
		testing = true;
		const sent = draft;
		const answer = await ai.test({
			provider,
			model: model.trim() || undefined,
			...(serverUrl ? { base_url: serverUrl } : {}),
			...(freshKey ? { api_key: freshKey } : {}),
			...(spec?.workspace ? { workspace_id: workspace } : {}),
			...(connection && keyStored && !freshKey ? { connection_id: connection.id } : {})
		});
		testing = false;
		tested = answer ? { draft: sent, result: answer } : null;
	}

	async function save() {
		attempted = true;
		if (missing()) return;
		const body = {
			name: name.trim() || undefined,
			provider,
			model: model.trim(),
			...(spec?.needs_base_url ? { base_url: serverUrl } : {}),
			...(freshKey ? { api_key: freshKey } : {}),
			...(spec?.workspace ? { workspace_id: workspace } : {})
		};
		const saved = editing ? await ai.update(editing.id, body) : await ai.create(body);
		if (!saved) return;
		toast.success(editing ? 'Provider saved' : 'Provider added');
		open = false;
	}
</script>

<Dialog.Root
	bind:open={() => open, (next) => (next ? (open = true) : !ai.isSaving && guard.close())}
>
	<Dialog.Content class="flex max-h-[85vh] flex-col gap-0 overflow-hidden p-0 sm:max-w-lg">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>{editing ? 'Edit provider' : 'Add provider'}</Dialog.Title>
			<Dialog.Description>The model AI features call.</Dialog.Description>
		</Dialog.Header>
		<ScrollArea
			class="min-h-0 flex-1 [&>[data-slot=scroll-area-viewport]]:max-h-[calc(85vh-10rem)]"
		>
			<div class="flex flex-col gap-4 px-6 py-5">
				<FormField
					label="Provider"
					description={spec?.help || undefined}
					error={errorFor('provider')}
					required
				>
					{#snippet children({ id })}
						<Select.Root type="single" value={provider} onValueChange={pickProvider}>
							<Select.Trigger {id} class="w-full">
								{spec?.label ?? 'Choose a provider'}
							</Select.Trigger>
							<Select.Content>
								{#each ai.catalog?.providers ?? [] as item (item.key)}
									<Select.Item value={item.key} label={item.label}>{item.label}</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
					{/snippet}
				</FormField>
				<FormField label="Name">
					{#snippet children({ id })}
						<Input
							{id}
							value={name}
							oninput={(e) => rename(e.currentTarget.value)}
							maxlength={MAX_CONNECTION_NAME}
							autocomplete="off"
						/>
					{/snippet}
				</FormField>
				{#if spec?.needs_base_url}
					<FormField
						label="Server URL"
						description={spec.base_url_hint || undefined}
						error={errorFor('url')}
						required
					>
						{#snippet children({ id })}
							<Input
								{id}
								bind:value={baseUrl}
								placeholder="https://"
								autocomplete="off"
								spellcheck={false}
								class="font-mono text-xs"
							/>
						{/snippet}
					</FormField>
				{/if}
				<FormField
					label="API key"
					error={errorFor('key')}
					required={!!spec && !spec.key_optional && !keyStored}
				>
					{#snippet children({ id })}
						<div class="relative">
							<Input
								{id}
								type={showKey ? 'text' : 'password'}
								bind:value={apiKey}
								placeholder={keyStored ? (connection?.key_masked ?? '') : (spec?.key_hint ?? '')}
								autocomplete="off"
								spellcheck={false}
								class="pr-10 font-mono text-xs"
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
				{#if spec?.workspace}
					<FormField label="Workspace ID" description="Required for keys not scoped to a workspace">
						{#snippet children({ id })}
							<Input
								{id}
								bind:value={workspaceId}
								autocomplete="off"
								spellcheck={false}
								class="font-mono text-xs"
							/>
						{/snippet}
					</FormField>
				{/if}
				<FormField label="Model" error={errorFor('model')} required>
					{#snippet children({ id })}
						<ModelPicker {id} {provider} {request} bind:value={model} />
					{/snippet}
				</FormField>
				{#if result}
					<p class="flex items-start gap-1.5 text-xs">
						{#if result.success}
							<CheckIcon class="mt-px size-3.5 shrink-0 text-success" />
						{:else}
							<CircleXIcon class="mt-px size-3.5 shrink-0 text-destructive" />
						{/if}
						<span class="wrap-anywhere">{result.message}</span>
					</p>
				{/if}
			</div>
		</ScrollArea>
		<Dialog.Footer class="gap-2 border-t px-6 py-4 sm:justify-between">
			<LoadingButton
				variant="ghost"
				loading={testing}
				loadingLabel="Testing"
				disabled={testing || ai.isSaving || !!missing()}
				onclick={() => test()}
			>
				Test connection
			</LoadingButton>
			<div class="flex gap-2">
				<Button variant="outline" disabled={ai.isSaving} onclick={() => guard.close()}>
					Cancel
				</Button>
				<LoadingButton loading={ai.isSaving} loadingLabel="Saving" onclick={() => save()}>
					{editing ? 'Save' : 'Add provider'}
				</LoadingButton>
			</div>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
