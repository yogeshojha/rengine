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
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import EmptyState from '$lib/components/empty-state.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import SettingRow from '$lib/components/settings/setting-row.svelte';
	import { ai } from '$lib/stores/ai.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { AIProvider } from '$lib/config/ai';
	import { routeLabels } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import * as Table from '$lib/components/ui/table/index.js';
	import { aiApi } from '$lib/api/ai';
	import type { AiCall, AiTestResult } from '$lib/types/ai';

	let dialogOpen = $state(false);
	let provider = $state<string>(AIProvider.ANTHROPIC);
	let model = $state('');
	let workspaceId = $state('');
	let baseUrl = $state('');
	let apiKey = $state('');
	let showKey = $state(false);
	let testing = $state(false);
	let draftResult = $state<AiTestResult | null>(null);
	let result = $state<AiTestResult | null>(null);

	let calls = $state<AiCall[]>([]);
	const status = $derived(ai.status);
	const catalog = $derived(ai.catalog);
	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const providerSpec = $derived(catalog?.providers.find((p) => p.key === provider));
	const stored = $derived(catalog?.providers.find((p) => p.key === status?.provider));
	function ktokens(n: number): string {
		return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
	}

	function outcome(call: AiCall): string {
		if (call.cached) return 'Cached';
		if (call.ok) return 'OK';
		return call.error ?? 'Failed';
	}

	$effect(() => {
		untrack(() => {
			void ai.fetch();
			void aiApi
				.calls(30)
				.then((rows) => (calls = rows))
				.catch(() => (calls = []));
		});
	});

	function modelLabel(spec: typeof stored, id: string | null): string {
		if (!id) return 'Not set';
		return spec?.models.find((m) => m.id === id)?.label ?? id;
	}

	function openEdit() {
		provider = status?.provider ?? AIProvider.ANTHROPIC;
		model = status?.model ?? '';
		workspaceId = status?.workspace_id ?? '';
		baseUrl = status?.base_url ?? '';
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
	}

	function draft() {
		return {
			provider,
			model: model.trim(),
			api_key: apiKey.trim() || undefined,
			workspace_id: provider === AIProvider.ANTHROPIC ? workspaceId.trim() : '',
			base_url: providerSpec?.needs_base_url ? baseUrl.trim() : ''
		};
	}

	async function testDraft() {
		testing = true;
		const body = draft();
		draftResult = await ai.test({
			provider: body.provider,
			model: body.model,
			api_key: body.api_key,
			workspace_id: body.workspace_id || undefined,
			base_url: body.base_url || undefined
		});
		testing = false;
	}

	async function testStored() {
		testing = true;
		result = await ai.test({ provider: status?.provider ?? AIProvider.ANTHROPIC });
		testing = false;
	}

	async function save() {
		const ok = await ai.save(draft());
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

{#snippet stat(label: string, value: string, sub: string | null)}
	<div class="flex flex-col gap-0.5 px-5 py-4">
		<span class="text-2xs tracking-wide text-muted-foreground uppercase">{label}</span>
		<span class="text-lg font-semibold tabular-nums">{value}</span>
		{#if sub}
			<span class="text-xs text-muted-foreground tabular-nums">{sub}</span>
		{/if}
	</div>
{/snippet}

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
		<SettingRow label="Provider" help={stored?.help} class="border-t-0">
			<span class="text-sm">{stored?.label ?? 'Not set'}</span>
		</SettingRow>
		<SettingRow label="Model">
			<span class="text-sm">{modelLabel(stored, status.model)}</span>
		</SettingRow>
		{#if stored?.needs_base_url}
			<SettingRow label="Server">
				<code class="font-mono text-xs text-muted-foreground">{status.base_url || 'Not set'}</code>
			</SettingRow>
		{/if}
		<SettingRow label="API key">
			<code class="font-mono text-xs text-muted-foreground">
				{status.key_masked ?? (stored?.key_optional ? 'None' : 'Not set')}
			</code>
		</SettingRow>
		{#if status.provider === AIProvider.ANTHROPIC}
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
		<PanelHead title="Features" class="border-t" />
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

		<div id="ai-usage" class="scroll-mt-20"></div>
		<PanelHead title="Usage" class="border-t">
			{#if status.usage.since || status.usage.ask.since}
				<span>Since {relativeTime(status.usage.since ?? status.usage.ask.since)}</span>
			{/if}
		</PanelHead>
		<div
			class="grid grid-cols-2 border-t sm:grid-cols-3 [&>*]:border-b [&>*]:border-l [&>*:nth-child(-n+3)]:border-t-0 [&>*:nth-child(2n+1)]:border-l-0 sm:[&>*:nth-child(2n+1)]:border-l sm:[&>*:nth-child(3n+1)]:border-l-0"
		>
			{@render stat(
				'Estimated spend',
				money(status.usage.cost_usd),
				`${status.usage.calls.toLocaleString()} ${status.usage.calls === 1 ? 'call' : 'calls'}${status.usage.failed ? ` · ${status.usage.failed} failed` : ''}`
			)}
			{#each status.usage.by_feature as f (f.feature)}
				{@render stat(
					f.label,
					f.calls.toLocaleString(),
					`${money(f.cost_usd)} · ${ktokens(f.input_tokens)} in · ${ktokens(f.output_tokens)} out${f.cached ? ` · ${f.cached} cached` : ''}${f.failed ? ` · ${f.failed} failed` : ''}`
				)}
			{/each}
			<div class="flex flex-col gap-0.5 px-5 py-4">
				<span class="text-2xs tracking-wide text-muted-foreground uppercase">Cached narratives</span
				>
				<span class="flex items-center gap-2 text-lg font-semibold tabular-nums">
					{status.cached_narratives.toLocaleString()}
					<Button
						variant="ghost"
						size="sm"
						class="h-7 px-2 text-xs font-normal"
						disabled={!isAdmin || !status.cached_narratives}
						onclick={clearCache}
					>
						Clear
					</Button>
				</span>
			</div>
		</div>
		{#if calls.length}
			<PanelHead title="Recent calls" class="border-t" />
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head class="pl-5">When</Table.Head>
						<Table.Head>Feature</Table.Head>
						<Table.Head>Model</Table.Head>
						<Table.Head class="text-right">Tokens in / out</Table.Head>
						<Table.Head class="text-right">Cost</Table.Head>
						<Table.Head class="pr-5">Outcome</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each calls as call (call.id)}
						<Table.Row>
							<Table.Cell class="pl-5 text-muted-foreground">{relativeTime(call.at)}</Table.Cell>
							<Table.Cell
								>{status.usage.by_feature.find((f) => f.feature === call.feature)?.label ??
									call.feature}</Table.Cell
							>
							<Table.Cell class="font-mono text-xs">{call.model}</Table.Cell>
							<Table.Cell class="text-right font-mono text-xs tabular-nums"
								>{call.input_tokens.toLocaleString()} / {call.output_tokens.toLocaleString()}</Table.Cell
							>
							<Table.Cell class="text-right tabular-nums">{money(call.cost_usd)}</Table.Cell>
							<Table.Cell class="max-w-64 truncate pr-5 {call.ok ? '' : 'text-destructive'}"
								>{outcome(call)}</Table.Cell
							>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		{/if}
		{#if !isAdmin}
			<div class="px-5 py-2.5 text-xs text-muted-foreground">Editable by administrators.</div>
		{/if}
	</Card.Root>
{/if}

<Dialog.Root bind:open={dialogOpen}>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>Edit connection</Dialog.Title>
		</Dialog.Header>
		<div class="flex flex-col gap-4">
			<FormField label="Provider" description={providerSpec?.help || undefined}>
				{#snippet children({ id })}
					<Select.Root type="single" value={provider} onValueChange={pickProvider}>
						<Select.Trigger {id} class="w-full">
							{providerSpec?.label ?? 'Choose a provider'}
						</Select.Trigger>
						<Select.Content>
							{#each catalog?.providers ?? [] as item (item.key)}
								<Select.Item value={item.key} label={item.label}>{item.label}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				{/snippet}
			</FormField>
			{#if providerSpec?.needs_base_url}
				<FormField label="Server URL" description={providerSpec.base_url_hint || undefined}>
					{#snippet children({ id })}
						<Input
							{id}
							bind:value={baseUrl}
							placeholder="https://"
							autocomplete="off"
							class="font-mono text-xs"
						/>
					{/snippet}
				</FormField>
			{/if}
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
			{#if provider === AIProvider.ANTHROPIC}
				<FormField label="Workspace ID" description="Required for keys not scoped to a workspace">
					{#snippet children({ id })}
						<Input {id} bind:value={workspaceId} autocomplete="off" class="font-mono text-xs" />
					{/snippet}
				</FormField>
			{/if}
			<FormField label="Model">
				{#snippet children({ id })}
					{#if providerSpec?.models.length}
						<Select.Root type="single" bind:value={model}>
							<Select.Trigger {id} class="w-full">
								{providerSpec.models.find((m) => m.id === model)?.label ?? model ?? 'Not set'}
							</Select.Trigger>
							<Select.Content>
								{#each providerSpec.models as item (item.id)}
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
					{:else}
						<Input
							{id}
							bind:value={model}
							placeholder="llama3.1, qwen2.5-coder, anthropic/claude-sonnet-4.5"
							autocomplete="off"
							class="font-mono text-xs"
						/>
					{/if}
				{/snippet}
			</FormField>
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
