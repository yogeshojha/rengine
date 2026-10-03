<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import CheckIcon from '@lucide/svelte/icons/check';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
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
	import {
		DEFAULT_AI_PROVIDER,
		MAX_CONNECTION_NAME,
		connectionName,
		optionPrice,
		parseRate,
		ratePair
	} from '$lib/config/ai';
	import type {
		AiConnection,
		AiConnectionCreate,
		AiModelOption,
		AiModelsRequest,
		AiTestResult
	} from '$lib/types/ai';

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
	let picked = $state<AiModelOption | null>(null);
	let listing = $state(false);
	let priceOpen = $state(false);
	let inputRate = $state('');
	let outputRate = $state('');
	let readRate = $state('');
	let writeRate = $state('');
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
	const listed = $derived(
		picked?.id === model.trim() && picked.input_per_mtok !== null && picked.output_per_mtok !== null
			? picked
			: null
	);
	const kept = $derived(
		sameServer && connection && !connection.custom_price && connection.model === model.trim()
			? connection
			: null
	);
	const basis = $derived(listed ?? kept);
	const typed = $derived([inputRate, outputRate, readRate, writeRate].map(parseRate));
	const customPrice = $derived(typed.some((rate) => rate !== undefined));
	const shownPrice = $derived.by(() => {
		const [input, output] = typed;
		if (customPrice && typeof input === 'number' && typeof output === 'number')
			return ratePair(input, output);
		if (basis?.input_per_mtok != null && basis.output_per_mtok != null)
			return ratePair(basis.input_per_mtok, basis.output_per_mtok);
		return listing ? '' : 'Not listed';
	});
	const placeholders = $derived(
		[
			basis?.input_per_mtok ?? 0,
			basis?.output_per_mtok ?? 0,
			basis?.cache_read_per_mtok,
			basis?.cache_write_per_mtok
		].map((rate) => (rate == null ? '' : rate ? String(rate) : '0.00'))
	);

	const form = $derived(
		JSON.stringify([
			provider,
			name.trim(),
			baseUrl.trim(),
			apiKey.trim(),
			workspaceId.trim(),
			model.trim(),
			inputRate,
			outputRate,
			readRate,
			writeRate
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
			priceOpen = false;
			typePrice(row?.custom_price ? row : null);
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
		pickModel(ai.provider(value)?.default_model ?? '');
	}

	function rename(value: string) {
		typedName = value;
		nameTouched = true;
	}

	type Field = 'provider' | 'url' | 'key' | 'model' | 'price';

	function missing(): { field: Field; message: string } | null {
		if (!spec) return { field: 'provider', message: 'Choose a provider' };
		if (spec.needs_base_url && !serverUrl)
			return { field: 'url', message: 'Server URL is required' };
		if (keyMissing) return { field: 'key', message: 'API key is required' };
		if (!model.trim()) return { field: 'model', message: 'Choose a model' };
		if (typed.some((rate) => rate === null))
			return { field: 'price', message: 'Price must be a number' };
		if (customPrice && (typed[0] === undefined || typed[1] === undefined))
			return { field: 'price', message: 'Input and output price are both required' };
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

	function priceFields(): Partial<AiConnectionCreate> {
		if (!customPrice) return { custom_price: false, ...optionPrice(listed) };
		const [input, output, read, write] = typed;
		return {
			custom_price: true,
			input_per_mtok: input ?? undefined,
			output_per_mtok: output ?? undefined,
			...(typeof read === 'number' ? { cache_read_per_mtok: read } : {}),
			...(typeof write === 'number' ? { cache_write_per_mtok: write } : {})
		};
	}

	function typePrice(row: AiConnection | null) {
		const text = (rate: number | null | undefined) => (rate == null ? '' : String(rate));
		inputRate = text(row?.input_per_mtok);
		outputRate = text(row?.output_per_mtok);
		readRate = text(row?.cache_read_per_mtok);
		writeRate = text(row?.cache_write_per_mtok);
	}

	function pickModel(value: string) {
		if (value === model) return;
		model = value;
		typePrice(
			sameServer && connection?.custom_price && connection.model === value ? connection : null
		);
	}

	async function save() {
		attempted = true;
		const reason = missing();
		if (reason) {
			if (reason.field === 'price') priceOpen = true;
			return;
		}
		const body = {
			name: name.trim() || undefined,
			provider,
			model: model.trim(),
			...priceFields(),
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
		</Dialog.Header>
		<ScrollArea
			class="min-h-0 flex-1 [&>[data-slot=scroll-area-viewport]]:max-h-[calc(85vh-10rem)]"
		>
			<div class="flex flex-col gap-4 px-6 py-5">
				<FormField
					label="Provider"
					description={spec?.help || undefined}
					error={errorFor('provider')}
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
				<FormField label="API key" error={errorFor('key')}>
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
				<FormField label="Model" error={errorFor('model')}>
					{#snippet children({ id })}
						<ModelPicker
							{id}
							{provider}
							{request}
							bind:value={() => model, pickModel}
							bind:selected={picked}
							bind:loading={listing}
						/>
					{/snippet}
				</FormField>
				{#if model.trim()}
					<Collapsible.Root bind:open={priceOpen}>
						<Collapsible.Trigger
							class="flex w-full items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
						>
							<ChevronRightIcon
								class="size-3 transition-transform {priceOpen ? 'rotate-90' : ''}"
							/>
							Price
							<span class="font-normal tabular-nums">{shownPrice}</span>
						</Collapsible.Trigger>
						<Collapsible.Content>
							<div class="grid grid-cols-2 gap-3 pt-3">
								<FormField label="Input per 1M tokens">
									{#snippet children({ id })}
										<Input
											{id}
											bind:value={inputRate}
											inputmode="decimal"
											placeholder={placeholders[0]}
											autocomplete="off"
											class="font-mono text-xs tabular-nums"
										/>
									{/snippet}
								</FormField>
								<FormField label="Output per 1M tokens">
									{#snippet children({ id })}
										<Input
											{id}
											bind:value={outputRate}
											inputmode="decimal"
											placeholder={placeholders[1]}
											autocomplete="off"
											class="font-mono text-xs tabular-nums"
										/>
									{/snippet}
								</FormField>
								<FormField label="Cache read per 1M tokens">
									{#snippet children({ id })}
										<Input
											{id}
											bind:value={readRate}
											inputmode="decimal"
											placeholder={placeholders[2]}
											autocomplete="off"
											class="font-mono text-xs tabular-nums"
										/>
									{/snippet}
								</FormField>
								<FormField label="Cache write per 1M tokens">
									{#snippet children({ id })}
										<Input
											{id}
											bind:value={writeRate}
											inputmode="decimal"
											placeholder={placeholders[3]}
											autocomplete="off"
											class="font-mono text-xs tabular-nums"
										/>
									{/snippet}
								</FormField>
							</div>
						</Collapsible.Content>
					</Collapsible.Root>
					{#if errorFor('price')}
						<p class="text-sm text-destructive" role="alert">{errorFor('price')}</p>
					{/if}
				{/if}
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
				disabled={testing || ai.isSaving}
				onclick={() => test()}
			>
				Test
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
