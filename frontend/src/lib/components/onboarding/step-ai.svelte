<script lang="ts">
	import { onMount } from 'svelte';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as RadioGroup from '$lib/components/ui/radio-group/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { toast } from 'svelte-sonner';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import { ai } from '$lib/stores/ai.svelte';
	import type { StepProps } from '$lib/types/onboarding';

	let { next, setFooter }: StepProps = $props();

	let enabled = $state(false);
	let provider = $state('');
	let apiKey = $state('');
	let model = $state('');
	let baseUrl = $state('');
	let showKey = $state(false);
	let features = $state<Record<string, boolean>>({});
	let testing = $state(false);

	const catalog = $derived(ai.catalog);
	const spec = $derived(catalog?.providers.find((p) => p.key === provider));

	onMount(async () => {
		await ai.fetch(true);
		const status = ai.status;
		const loaded = ai.catalog;
		if (!status || !loaded) return;
		enabled = status.enabled;
		provider = status.provider ?? loaded.providers[0]?.key ?? '';
		model = status.model ?? '';
		baseUrl = status.base_url ?? '';
		features = Object.fromEntries(
			loaded.features.map((f) => [f.key, status.features[f.key] ?? f.default])
		);
	});

	$effect(() => {
		setFooter({
			onNext: handleNext,
			nextLabel: 'Continue',
			nextLoading: ai.isSaving,
			nextDisabled: testing,
			canSkip: true
		});
	});

	function selectProvider(v: string) {
		if (!v || v === provider) return;
		provider = v;
		model = catalog?.providers.find((p) => p.key === v)?.models[0]?.id ?? '';
	}

	function serverUrl(): string {
		return spec?.needs_base_url ? baseUrl.trim() : '';
	}

	async function handleTest() {
		testing = true;
		const result = await ai.test({
			provider,
			model: model.trim() || undefined,
			api_key: apiKey.trim() || undefined,
			base_url: serverUrl() || undefined
		});
		testing = false;
		if (!result) return;
		if (result.success) toast.success(result.message);
		else toast.error(result.message);
	}

	async function handleNext() {
		if (!enabled) {
			if (await ai.save({ enabled: false })) next();
			return;
		}
		if (spec?.needs_base_url && !serverUrl()) {
			toast.error('Server URL is required');
			return;
		}
		if (!spec?.key_optional && !apiKey.trim() && !ai.status?.key_masked) {
			toast.error('API key is required');
			return;
		}
		const saved = await ai.save({
			enabled: true,
			provider,
			model: model.trim(),
			api_key: apiKey.trim() || undefined,
			base_url: serverUrl(),
			features
		});
		if (saved) next();
	}
</script>

<div class="space-y-6">
	<div class="flex items-center justify-between rounded-lg border px-4 py-3">
		<div class="space-y-0.5">
			<Label class="text-sm font-medium">Enable AI analysis</Label>
			<p class="text-xs text-muted-foreground">Connect an external LLM provider.</p>
		</div>
		<Switch
			checked={enabled}
			onCheckedChange={(v) => (enabled = v)}
			disabled={ai.isSaving || !catalog}
		/>
	</div>

	{#if enabled && catalog}
		<Alert.Root variant="destructive">
			<TriangleAlertIcon />
			<Alert.Title>Scan data is sent to the provider</Alert.Title>
			<Alert.Description>Includes targets, findings and scan context.</Alert.Description>
		</Alert.Root>

		<div class="space-y-2">
			<Label class="text-xs">Provider</Label>
			<RadioGroup.Root
				value={provider}
				onValueChange={selectProvider}
				class="grid grid-cols-2 gap-2 sm:grid-cols-4"
			>
				{#each catalog.providers as p (p.key)}
					<Label
						class="flex cursor-pointer items-center gap-2 rounded-md border border-input bg-transparent px-3 py-2 text-sm data-[active=true]:border-primary data-[active=true]:bg-muted"
						data-active={provider === p.key}
					>
						<RadioGroup.Item value={p.key} />
						<span class="truncate">{p.label}</span>
					</Label>
				{/each}
			</RadioGroup.Root>
			{#if spec?.help}
				<p class="text-xs text-muted-foreground">{spec.help}</p>
			{/if}
		</div>

		{#if spec?.needs_base_url}
			<div class="space-y-1.5">
				<Label class="text-xs" for="ai-base-url">Server URL</Label>
				<Input
					id="ai-base-url"
					bind:value={baseUrl}
					placeholder="https://"
					autocomplete="off"
					class="h-9 font-mono text-xs"
					disabled={ai.isSaving}
				/>
				{#if spec.base_url_hint}
					<p class="text-xs text-muted-foreground">{spec.base_url_hint}</p>
				{/if}
			</div>
		{/if}

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<div class="space-y-1.5">
				<Label class="text-xs" for="ai-key">
					API key
					{#if spec?.key_optional}<span class="text-muted-foreground">Optional</span>{/if}
				</Label>
				<div class="relative">
					<Input
						id="ai-key"
						type={showKey ? 'text' : 'password'}
						bind:value={apiKey}
						placeholder={ai.status?.key_masked ?? spec?.key_hint ?? ''}
						autocomplete="off"
						class="h-9 pr-9 font-mono text-xs"
						disabled={ai.isSaving}
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
			</div>
			<div class="space-y-1.5">
				<Label class="text-xs" for="ai-model">Model</Label>
				{#if spec?.models.length}
					<Select.Root type="single" bind:value={model} disabled={ai.isSaving}>
						<Select.Trigger id="ai-model" class="h-9 w-full text-xs">
							{spec.models.find((m) => m.id === model)?.label ?? model}
						</Select.Trigger>
						<Select.Content>
							{#each spec.models as m (m.id)}
								<Select.Item value={m.id} label={m.label}>{m.label}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
				{:else}
					<Input
						id="ai-model"
						bind:value={model}
						placeholder="llama3.1"
						autocomplete="off"
						class="h-9 font-mono text-xs"
						disabled={ai.isSaving}
					/>
				{/if}
			</div>
		</div>

		<div>
			<LoadingButton
				variant="outline"
				size="sm"
				class="h-8 text-xs"
				loading={testing}
				loadingLabel="Testing"
				disabled={ai.isSaving}
				onclick={handleTest}
			>
				<FlaskConicalIcon class="mr-1.5 size-3" />
				Test connection
			</LoadingButton>
		</div>

		<Separator />

		<div class="space-y-3">
			<Label class="text-xs">Features</Label>
			<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
				{#each catalog.features as f (f.key)}
					<Label
						class="flex cursor-pointer items-start gap-3 rounded-md border border-input px-3 py-2.5 data-[active=true]:border-primary data-[active=true]:bg-muted"
						data-active={features[f.key]}
					>
						<Checkbox
							checked={features[f.key]}
							onCheckedChange={(v) => (features = { ...features, [f.key]: v === true })}
							class="mt-0.5"
						/>
						<span class="space-y-0.5">
							<span class="block text-sm font-medium">{f.label}</span>
							<span class="block text-xs text-muted-foreground">{f.help}</span>
						</span>
					</Label>
				{/each}
			</div>
		</div>
	{/if}
</div>
