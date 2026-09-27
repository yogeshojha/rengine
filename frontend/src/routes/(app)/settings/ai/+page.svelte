<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import CpuIcon from '@lucide/svelte/icons/cpu';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as ToggleGroup from '$lib/components/ui/toggle-group/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import EmptyState from '$lib/components/empty-state.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import SettingRow from '$lib/components/settings/setting-row.svelte';
	import { ai } from '$lib/stores/ai.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { routeLabels } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import type { AiTestResult } from '$lib/types/ai';

	const ANTHROPIC = 'anthropic';

	let dialogOpen = $state(false);
	let provider = $state(ANTHROPIC);
	let model = $state('');
	let fastModel = $state('');
	let workspaceId = $state('');
	let apiKey = $state('');
	let showKey = $state(false);
	let testing = $state(false);
	let draftResult = $state<AiTestResult | null>(null);
	let result = $state<AiTestResult | null>(null);

	const status = $derived(ai.status);
	const catalog = $derived(ai.catalog);
	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const providerSpec = $derived(catalog?.providers.find((p) => p.key === provider));
	const stored = $derived(catalog?.providers.find((p) => p.key === status?.provider));

	$effect(() => {
		untrack(() => void ai.fetch());
	});

	function modelLabel(spec: typeof stored, id: string | null): string {
		if (!id) return 'Not set';
		return spec?.models.find((m) => m.id === id)?.label ?? id;
	}

	function openEdit() {
		provider = status?.provider ?? ANTHROPIC;
		model = status?.model ?? '';
		fastModel = status?.fast_model ?? '';
		workspaceId = status?.workspace_id ?? '';
		apiKey = '';
		showKey = false;
		draftResult = null;
		dialogOpen = true;
	}

	function pickProvider(value: string) {
		if (!value || value === provider) return;
		provider = value;
		const spec = catalog?.providers.find((p) => p.key === value);
		model = spec?.models[0]?.id ?? '';
		fastModel = spec?.models.at(-1)?.id ?? model;
	}

	async function testDraft() {
		testing = true;
		draftResult = await ai.test({
			provider,
			model,
			api_key: apiKey.trim() || undefined,
			workspace_id: workspaceId.trim() || undefined
		});
		testing = false;
	}

	async function testStored() {
		testing = true;
		result = await ai.test({ provider: status?.provider ?? ANTHROPIC });
		testing = false;
	}

	async function save() {
		const ok = await ai.save({
			provider,
			model,
			fast_model: fastModel,
			workspace_id: provider === ANTHROPIC ? workspaceId.trim() : '',
			api_key: apiKey.trim() || undefined
		});
		if (ok) {
			toast.success('Connection saved');
			result = null;
			dialogOpen = false;
		}
	}

	async function setEnabled(value: boolean) {
		if (await ai.save({ enabled: value })) toast.success(value ? 'AI enabled' : 'AI disabled');
	}

	async function setFeature(key: string, label: string, value: boolean) {
		if (await ai.save({ features: { [key]: value } })) {
			toast.success(`${label} ${value ? 'enabled' : 'disabled'}`);
		}
	}

	async function clearCache() {
		const removed = await ai.clearCache();
		toast.success(`${removed.toLocaleString()} cached narratives removed`);
	}

	function money(value: number | null): string {
		return value === null ? '—' : `$${value.toFixed(2)}`;
	}
</script>

<svelte:head><title>{pageTitle(routeLabels.ai)}</title></svelte:head>

{#if ai.isLoading && !status}
	<Card.Root class="gap-3 p-5">
		<Skeleton class="h-4 w-24" />
		<Skeleton class="h-9 w-full" />
		<Skeleton class="h-9 w-full" />
	</Card.Root>
{:else if !status}
	<EmptyState compact icon={CpuIcon} title="AI settings not loaded">
		<Button variant="outline" size="sm" onclick={() => ai.fetch(true)}>Retry</Button>
	</EmptyState>
{:else}
	<div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
		<Card.Root class="gap-0 overflow-hidden py-0">
			<div id="ai-connection" class="scroll-mt-20"></div>
			<PanelHead title="Connection">
				<label class="flex items-center gap-2 text-sm text-foreground" for="ai-enabled">
					Enabled
					<Switch
						id="ai-enabled"
						checked={status.enabled}
						disabled={!isAdmin || !status.configured || ai.isSaving}
						onCheckedChange={setEnabled}
					/>
				</label>
			</PanelHead>
			<SettingRow label="Provider" class="border-t-0">
				<span class="text-sm">{stored?.label ?? 'Not set'}</span>
			</SettingRow>
			<SettingRow label="Model">
				<span class="text-sm">{modelLabel(stored, status.model)}</span>
			</SettingRow>
			<SettingRow label="Fast model" help="Asset judgement, finding explanations and attack paths">
				<span class="text-sm">{modelLabel(stored, status.fast_model)}</span>
			</SettingRow>
			<SettingRow label="API key">
				<code class="font-mono text-xs text-muted-foreground">
					{status.key_masked ?? 'Not set'}
				</code>
			</SettingRow>
			{#if status.provider === ANTHROPIC}
				<SettingRow label="Workspace ID">
					<code class="font-mono text-xs text-muted-foreground">
						{status.workspace_id || 'Not set'}
					</code>
				</SettingRow>
			{/if}
			<div class="flex flex-wrap items-center gap-2 border-t px-5 py-3">
				<Button variant="outline" size="sm" disabled={!isAdmin} onclick={openEdit}>
					Edit connection
				</Button>
				<LoadingButton
					variant="ghost"
					size="sm"
					loading={testing && !dialogOpen}
					loadingLabel="Testing"
					disabled={!isAdmin || !status.configured || testing}
					onclick={testStored}
				>
					Test connection
				</LoadingButton>
				{#if result}
					<span class="flex min-w-0 items-center gap-1.5 text-xs">
						{#if result.success}
							<CheckIcon class="size-3.5 shrink-0 text-success" />
						{:else}
							<CircleXIcon class="size-3.5 shrink-0 text-destructive" />
						{/if}
						<span class="wrap-anywhere">{result.message}</span>
					</span>
				{/if}
			</div>

			<div id="ai-features" class="scroll-mt-20"></div>
			<div class="border-t px-5 pt-4 pb-2">
				<h2 class="text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase">
					Features
				</h2>
			</div>
			{#each catalog?.features ?? [] as feature, i (feature.key)}
				<SettingRow
					label={feature.label}
					help={feature.help}
					for="ai-feature-{feature.key}"
					class={i === 0 ? 'border-t-0' : ''}
				>
					<Switch
						id="ai-feature-{feature.key}"
						checked={status.features[feature.key] ?? feature.default}
						disabled={!isAdmin || ai.isSaving}
						onCheckedChange={(v) => setFeature(feature.key, feature.label, v)}
					/>
				</SettingRow>
			{/each}
			{#if !isAdmin}
				<div class="border-t px-5 py-2.5 text-xs text-muted-foreground">
					Editable by administrators.
				</div>
			{/if}
		</Card.Root>

		<Card.Root class="h-fit gap-0 overflow-hidden py-0">
			<div id="ai-usage" class="scroll-mt-20"></div>
			<PanelHead title="Usage">
				{#if status.usage.since}
					<span>Since {relativeTime(status.usage.since)}</span>
				{/if}
			</PanelHead>
			<dl class="divide-y text-sm">
				<div class="flex items-baseline justify-between px-5 py-2.5">
					<dt class="text-muted-foreground">Reports written</dt>
					<dd class="tabular-nums">{status.usage.reports.toLocaleString()}</dd>
				</div>
				<div class="flex items-baseline justify-between px-5 py-2.5">
					<dt class="text-muted-foreground">Model calls</dt>
					<dd class="tabular-nums">{status.usage.calls.toLocaleString()}</dd>
				</div>
				<div class="flex items-baseline justify-between px-5 py-2.5">
					<dt class="text-muted-foreground">Served from cache</dt>
					<dd class="tabular-nums">{status.usage.cached.toLocaleString()}</dd>
				</div>
				<div class="flex items-baseline justify-between px-5 py-2.5">
					<dt class="text-muted-foreground">Tokens in / out</dt>
					<dd class="tabular-nums">
						{status.usage.input_tokens.toLocaleString()} / {status.usage.output_tokens.toLocaleString()}
					</dd>
				</div>
				<div class="flex items-baseline justify-between px-5 py-2.5">
					<dt class="text-muted-foreground">Estimated spend</dt>
					<dd class="tabular-nums">{money(status.usage.cost_usd)}</dd>
				</div>
				<div class="flex items-center justify-between gap-3 px-5 py-2">
					<dt class="text-muted-foreground">Cached narratives</dt>
					<dd class="flex items-center gap-2 tabular-nums">
						{status.cached_narratives.toLocaleString()}
						<Hint text="Cleared narratives are rewritten and billed on the next report">
							{#snippet child(props)}
								<span {...props} class="inline-flex">
									<Button
										variant="ghost"
										size="sm"
										class="h-7 px-2"
										disabled={!isAdmin || !status.cached_narratives}
										onclick={clearCache}
									>
										Clear
									</Button>
								</span>
							{/snippet}
						</Hint>
					</dd>
				</div>
			</dl>
		</Card.Root>
	</div>
{/if}

<Dialog.Root bind:open={dialogOpen}>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>Edit connection</Dialog.Title>
		</Dialog.Header>
		<div class="flex flex-col gap-4">
			<FormField label="Provider">
				{#snippet children({ id })}
					<ToggleGroup.Root
						{id}
						type="single"
						variant="outline"
						value={provider}
						onValueChange={pickProvider}
						class="w-fit flex-wrap"
						aria-label="Provider"
					>
						{#each catalog?.providers ?? [] as item (item.key)}
							<ToggleGroup.Item value={item.key} class="h-9 px-3 text-sm font-normal">
								{item.label}
							</ToggleGroup.Item>
						{/each}
					</ToggleGroup.Root>
				{/snippet}
			</FormField>
			<FormField label="API key">
				{#snippet children({ id })}
					<div class="relative">
						<Input
							{id}
							type={showKey ? 'text' : 'password'}
							bind:value={apiKey}
							placeholder={status?.key_masked ?? providerSpec?.key_hint ?? ''}
							autocomplete="off"
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
			{#if provider === ANTHROPIC}
				<FormField label="Workspace ID" description="Required for keys not scoped to a workspace">
					{#snippet children({ id })}
						<Input {id} bind:value={workspaceId} autocomplete="off" class="font-mono text-xs" />
					{/snippet}
				</FormField>
			{/if}
			<div class="grid gap-4 sm:grid-cols-2">
				<FormField label="Model">
					{#snippet children({ id })}
						<Select.Root type="single" bind:value={model}>
							<Select.Trigger {id} class="w-full">
								{providerSpec?.models.find((m) => m.id === model)?.label ?? 'Not set'}
							</Select.Trigger>
							<Select.Content>
								{#each providerSpec?.models ?? [] as item (item.id)}
									<Select.Item value={item.id} label={item.label}>
										<span class="flex flex-col items-start gap-0.5">
											<span>{item.label}</span>
											{#if item.input_per_mtok}
												<span class="text-xs text-muted-foreground">
													${item.input_per_mtok} in · ${item.output_per_mtok} out per million tokens
												</span>
											{/if}
										</span>
									</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
					{/snippet}
				</FormField>
				<FormField label="Fast model">
					{#snippet children({ id })}
						<Select.Root type="single" bind:value={fastModel}>
							<Select.Trigger {id} class="w-full">
								{providerSpec?.models.find((m) => m.id === fastModel)?.label ?? 'Not set'}
							</Select.Trigger>
							<Select.Content>
								{#each providerSpec?.models ?? [] as item (item.id)}
									<Select.Item value={item.id} label={item.label}>{item.label}</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
					{/snippet}
				</FormField>
			</div>
			{#if draftResult}
				<p class="flex items-start gap-1.5 text-xs">
					{#if draftResult.success}
						<CheckIcon class="mt-px size-3.5 shrink-0 text-success" />
					{:else}
						<CircleXIcon class="mt-px size-3.5 shrink-0 text-destructive" />
					{/if}
					<span class="wrap-anywhere">{draftResult.message}</span>
				</p>
			{/if}
		</div>
		<Dialog.Footer class="gap-2 sm:justify-between">
			<LoadingButton
				variant="ghost"
				loading={testing && dialogOpen}
				loadingLabel="Testing"
				disabled={testing || ai.isSaving}
				onclick={testDraft}
			>
				Test
			</LoadingButton>
			<div class="flex gap-2">
				<Button variant="outline" disabled={ai.isSaving} onclick={() => (dialogOpen = false)}>
					Cancel
				</Button>
				<LoadingButton loading={ai.isSaving} loadingLabel="Saving" onclick={save}>
					Save connection
				</LoadingButton>
			</div>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
