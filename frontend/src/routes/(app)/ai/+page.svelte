<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import ShieldAlertIcon from '@lucide/svelte/icons/shield-alert';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import PanelHead from '$lib/components/panel-head.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { ai } from '$lib/stores/ai.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { routeLabels } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import { toast } from 'svelte-sonner';
	import type { AiTestResult } from '$lib/types/ai';

	let provider = $state('anthropic');
	let model = $state('');
	let fastModel = $state('');
	let workspaceId = $state('');
	let apiKey = $state('');
	let showKey = $state(false);
	let testing = $state(false);
	let result = $state<AiTestResult | null>(null);
	let loaded = $state(false);

	const status = $derived(ai.status);
	const catalog = $derived(ai.catalog);
	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const providerSpec = $derived(catalog?.providers.find((p) => p.key === provider));
	const isAnthropic = $derived(provider === 'anthropic');

	$effect(() => {
		void ai.fetch();
	});

	$effect(() => {
		const current = status;
		if (!current || loaded) return;
		loaded = true;
		provider = current.provider ?? 'anthropic';
		model = current.model ?? '';
		fastModel = current.fast_model ?? '';
		workspaceId = current.workspace_id ?? '';
	});

	function pickProvider(value: string) {
		provider = value;
		const spec = catalog?.providers.find((p) => p.key === value);
		model = spec?.models[0]?.id ?? '';
		fastModel = spec?.models.at(-1)?.id ?? model;
	}

	async function test() {
		testing = true;
		result = await ai.test({
			provider,
			model,
			api_key: apiKey.trim() || undefined,
			workspace_id: workspaceId.trim() || undefined
		});
		testing = false;
	}

	async function save() {
		const ok = await ai.save({
			provider,
			model,
			fast_model: fastModel,
			workspace_id: workspaceId.trim(),
			api_key: apiKey.trim() || undefined
		});
		if (ok) {
			apiKey = '';
			toast.success('Saved.');
		}
	}

	async function setEnabled(value: boolean) {
		const ok = await ai.save({ enabled: value });
		if (ok) toast.success(value ? 'AI is on for this instance.' : 'AI is off.');
	}

	async function setFeature(key: string, value: boolean) {
		await ai.save({ features: { [key]: value } });
	}

	async function clearCache() {
		const removed = await ai.clearCache();
		toast.success(`${removed} cached passages removed.`);
	}

	function money(value: number | null): string {
		return value === null ? '—' : `$${value.toFixed(2)}`;
	}
</script>

<svelte:head><title>{routeLabels.ai} · reNgine</title></svelte:head>

<div class="space-y-6">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div>
			<h1 class="flex items-center gap-2 text-2xl font-semibold tracking-tight">
				<SparklesIcon class="size-5" />
				{routeLabels.ai}
			</h1>
			<p class="mt-1 max-w-2xl text-sm text-muted-foreground">
				Model connection, feature opt-ins and usage for report narratives
			</p>
		</div>
		{#if status}
			<div class="flex items-center gap-3 rounded-md border px-3 py-2">
				<span class="text-sm">{status.enabled ? 'On' : 'Off'}</span>
				<Switch
					checked={status.enabled}
					disabled={!isAdmin || !status.configured}
					onCheckedChange={setEnabled}
				/>
			</div>
		{/if}
	</div>

	{#if ai.isLoading && !status}
		<Skeleton class="h-64 w-full" />
	{:else if status}
		<Alert.Root variant="destructive">
			<ShieldAlertIcon />
			<Alert.Title>Scan data is sent to the configured provider</Alert.Title>
			<Alert.Description>
				Report narration sends a computed summary of the scan: counts, severity totals, check names
				and detected conditions. Request and response bodies, credentials and scan context headers
				are never sent. Disable on air-gapped or restricted deployments.
			</Alert.Description>
		</Alert.Root>

		<div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
			<Card.Root class="gap-0 py-0">
				<PanelHead title="Connection" description="Provider and model used for narratives" />
				<div class="space-y-5 px-5 py-5">
					<div class="space-y-2">
						<Label class="text-xs">Provider</Label>
						<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
							{#each catalog?.providers ?? [] as item (item.key)}
								<button
									type="button"
									class="rounded-md border px-3 py-2 text-sm transition-colors data-[active=true]:border-primary data-[active=true]:bg-muted"
									data-active={provider === item.key}
									disabled={!isAdmin}
									onclick={() => pickProvider(item.key)}
								>
									{item.label}
								</button>
							{/each}
						</div>
					</div>

					<div class="grid gap-4 sm:grid-cols-2">
						<div class="space-y-1.5">
							<Label class="text-xs" for="ai-key">API key</Label>
							<div class="relative">
								<Input
									id="ai-key"
									type={showKey ? 'text' : 'password'}
									bind:value={apiKey}
									placeholder={status.key_masked ?? providerSpec?.key_hint ?? 'Paste the API key'}
									autocomplete="off"
									disabled={!isAdmin}
									class="h-9 pr-9 font-mono text-xs"
								/>
								<button
									type="button"
									class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
									onclick={() => (showKey = !showKey)}
									aria-label={showKey ? 'Hide key' : 'Show key'}
								>
									{#if showKey}<EyeOffIcon class="size-4" />{:else}<EyeIcon class="size-4" />{/if}
								</button>
							</div>
							{#if status.configured}
								<p class="text-xs text-muted-foreground">
									A key is stored. Leave this empty to keep it.
								</p>
							{/if}
						</div>

						{#if isAnthropic}
							<div class="space-y-1.5">
								<Label class="text-xs" for="ai-workspace">Workspace ID</Label>
								<Input
									id="ai-workspace"
									bind:value={workspaceId}
									placeholder="Only for keys not scoped to a workspace"
									disabled={!isAdmin}
									class="h-9 font-mono text-xs"
								/>
								<p class="text-xs text-muted-foreground">
									Leave empty unless the provider asks for it.
								</p>
							</div>
						{/if}

						<div class="space-y-1.5">
							<Label class="text-xs">Model for narrative</Label>
							<Select.Root type="single" bind:value={model}>
								<Select.Trigger class="h-9 w-full" disabled={!isAdmin}>
									{providerSpec?.models.find((m) => m.id === model)?.label ??
										(model || 'Choose a model')}
								</Select.Trigger>
								<Select.Content>
									{#each providerSpec?.models ?? [] as item (item.id)}
										<Select.Item value={item.id}>
											<span class="flex flex-col items-start gap-0.5">
												<span>{item.label}</span>
												{#if item.input_per_mtok}
													<span class="text-xs text-muted-foreground">
														${item.input_per_mtok} in / ${item.output_per_mtok} out per million tokens
													</span>
												{/if}
											</span>
										</Select.Item>
									{/each}
								</Select.Content>
							</Select.Root>
						</div>

						<div class="space-y-1.5">
							<Label class="text-xs">Model for per-check explanations</Label>
							<Select.Root type="single" bind:value={fastModel}>
								<Select.Trigger class="h-9 w-full" disabled={!isAdmin}>
									{providerSpec?.models.find((m) => m.id === fastModel)?.label ??
										(fastModel || 'Choose a model')}
								</Select.Trigger>
								<Select.Content>
									{#each providerSpec?.models ?? [] as item (item.id)}
										<Select.Item value={item.id}>{item.label}</Select.Item>
									{/each}
								</Select.Content>
							</Select.Root>
							<p class="text-xs text-muted-foreground">
								Written once per check and cached. A lower-cost model is sufficient.
							</p>
						</div>
					</div>

					{#if result}
						<Alert.Root variant={result.success ? 'default' : 'destructive'}>
							{#if result.success}<CheckIcon />{:else}<CircleXIcon />{/if}
							<Alert.Title>{result.success ? 'Connected' : 'That did not work'}</Alert.Title>
							<Alert.Description class="wrap-anywhere">{result.message}</Alert.Description>
						</Alert.Root>
					{/if}

					<div class="flex items-center gap-2">
						<LoadingButton variant="outline" loading={testing} disabled={!isAdmin} onclick={test}>
							<FlaskConicalIcon class="mr-1.5 size-3.5" />
							Test connection
						</LoadingButton>
						<LoadingButton loading={ai.isSaving} disabled={!isAdmin} onclick={save}>
							Save
						</LoadingButton>
					</div>
					{#if !isAdmin}
						<p class="text-xs text-muted-foreground">
							Only an administrator can change these settings.
						</p>
					{/if}
				</div>

				<Separator />

				<PanelHead title="Features" description="Each is opt in per report" />
				<div class="space-y-4 px-5 py-5">
					{#each catalog?.features ?? [] as feature (feature.key)}
						<div class="flex items-start justify-between gap-4">
							<div class="space-y-0.5">
								<span class="text-sm font-medium">{feature.label}</span>
								<p class="text-xs text-muted-foreground">{feature.help}</p>
							</div>
							<Switch
								checked={status.features[feature.key] ?? feature.default}
								disabled={!isAdmin}
								onCheckedChange={(v) => setFeature(feature.key, v)}
							/>
						</div>
					{/each}
				</div>
			</Card.Root>

			<div class="space-y-5">
				<Card.Root class="gap-0 py-0">
					<PanelHead title="Usage" description="Across every report on this instance" />
					<div class="divide-y">
						<div class="flex items-baseline justify-between px-5 py-3">
							<span class="text-sm text-muted-foreground">Reports written</span>
							<span class="font-medium">{status.usage.reports.toLocaleString()}</span>
						</div>
						<div class="flex items-baseline justify-between px-5 py-3">
							<span class="text-sm text-muted-foreground">Model calls</span>
							<span class="font-medium">{status.usage.calls.toLocaleString()}</span>
						</div>
						<div class="flex items-baseline justify-between px-5 py-3">
							<span class="text-sm text-muted-foreground">Served from cache</span>
							<span class="font-medium">{status.usage.cached.toLocaleString()}</span>
						</div>
						<div class="flex items-baseline justify-between px-5 py-3">
							<span class="text-sm text-muted-foreground">Tokens in / out</span>
							<span class="font-medium">
								{status.usage.input_tokens.toLocaleString()} / {status.usage.output_tokens.toLocaleString()}
							</span>
						</div>
						<div class="flex items-baseline justify-between px-5 py-3">
							<span class="text-sm text-muted-foreground">Estimated spend</span>
							<span class="font-medium">{money(status.usage.cost_usd)}</span>
						</div>
						{#if status.usage.since}
							<div class="px-5 py-2.5 text-xs text-muted-foreground">
								Since {relativeTime(status.usage.since)}
							</div>
						{/if}
					</div>
				</Card.Root>

				<Card.Root class="gap-0 py-0">
					<PanelHead
						title="Written passages"
						description="Cached narratives, keyed by the input they were written from"
					/>
					<div class="space-y-3 px-5 py-4">
						<div class="flex items-baseline justify-between">
							<span class="text-sm text-muted-foreground">Cached</span>
							<Badge variant="secondary">{status.cached_narratives.toLocaleString()}</Badge>
						</div>
						<p class="text-xs text-muted-foreground">
							Clearing the cache means the next report is charged for its narrative again.
						</p>
						<Button
							variant="outline"
							size="sm"
							class="w-full"
							disabled={!isAdmin || !status.cached_narratives}
							onclick={clearCache}
						>
							Clear the cache
						</Button>
					</div>
				</Card.Root>
			</div>
		</div>
	{/if}
</div>
