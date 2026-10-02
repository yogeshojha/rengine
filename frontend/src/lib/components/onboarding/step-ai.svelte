<script lang="ts">
	import { onMount } from 'svelte';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as RadioGroup from '$lib/components/ui/radio-group/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ModelPicker from '$lib/components/settings/model-picker.svelte';
	import { toast } from 'svelte-sonner';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import { aiApi } from '$lib/api/ai';
	import { ai } from '$lib/stores/ai.svelte';
	import { optionPrice } from '$lib/config/ai';
	import type { AiConnection, AiModelOption, AiModelsRequest } from '$lib/types/ai';
	import type { StepProps } from '$lib/types/onboarding';

	let { next, setFooter }: StepProps = $props();

	const SERVER_URL = /^https?:\/\/[^/\s]+/i;

	let enabled = $state(false);
	let provider = $state('');
	let apiKey = $state('');
	let model = $state('');
	let picked = $state<AiModelOption | null>(null);
	let baseUrl = $state('');
	let showKey = $state(false);
	let features = $state<Record<string, boolean>>({});
	let testing = $state(false);
	let saving = $state(false);
	let saved = $state<AiConnection | null>(null);

	const catalog = $derived(ai.catalog);
	const spec = $derived(ai.provider(provider));
	const serverUrl = $derived(spec?.needs_base_url ? baseUrl.trim() : '');
	const freshKey = $derived(apiKey.trim());
	const keyStored = $derived(
		!!saved?.key_masked &&
			saved.provider === provider &&
			(saved.base_url ?? '') === serverUrl.replace(/\/+$/, '')
	);
	const keyMissing = $derived(!!spec && !spec.key_optional && !freshKey && !keyStored);
	const reuse = $derived(saved && keyStored && !freshKey ? { connection_id: saved.id } : {});

	const request = $derived.by((): AiModelsRequest | null => {
		if (!spec || keyMissing) return null;
		if (spec.needs_base_url && !SERVER_URL.test(serverUrl)) return null;
		return {
			provider,
			...(serverUrl ? { base_url: serverUrl } : {}),
			...(freshKey ? { api_key: freshKey } : {}),
			...reuse
		};
	});

	onMount(async () => {
		const [, step] = await Promise.all([ai.fetch(true), aiApi.onboarding().catch(() => null)]);
		const loaded = ai.catalog;
		if (!loaded) return;
		saved = step?.connection ?? null;
		enabled = step?.enabled ?? false;
		provider = saved?.provider ?? loaded.providers[0]?.key ?? '';
		model = saved?.model ?? ai.provider(provider)?.default_model ?? '';
		baseUrl = saved?.base_url ?? '';
		features = Object.fromEntries(
			loaded.features.map((f) => [f.key, step?.features[f.key] ?? f.default])
		);
	});

	$effect(() => {
		setFooter({
			onNext: handleNext,
			nextLabel: 'Continue',
			nextLoading: saving,
			nextDisabled: testing,
			canSkip: true
		});
	});

	function selectProvider(v: string) {
		if (!v || v === provider) return;
		provider = v;
		model = ai.provider(v)?.default_model ?? '';
	}

	async function handleTest() {
		testing = true;
		const result = await ai.test({
			provider,
			model: model.trim() || undefined,
			...(serverUrl ? { base_url: serverUrl } : {}),
			...(freshKey ? { api_key: freshKey } : {}),
			...reuse
		});
		testing = false;
		if (!result) return;
		if (result.success) toast.success(result.message);
		else toast.error(result.message);
	}

	function listedPrice() {
		return optionPrice(picked?.id === model.trim() ? picked : null);
	}

	async function handleNext() {
		if (enabled && spec?.needs_base_url && !serverUrl) {
			toast.error('Server URL is required');
			return;
		}
		if (enabled && keyMissing) {
			toast.error('API key is required');
			return;
		}
		if (enabled && !model.trim()) {
			toast.error('Choose a model');
			return;
		}
		saving = true;
		try {
			const step = await aiApi.saveOnboarding(
				enabled
					? {
							enabled: true,
							provider,
							model: model.trim(),
							...listedPrice(),
							features,
							...(serverUrl ? { base_url: serverUrl } : {}),
							...(freshKey ? { api_key: freshKey } : {})
						}
					: { enabled: false }
			);
			saved = step.connection;
			apiKey = '';
			void ai.fetch(true);
			if (saved?.in_use && !saved.last_test_at) void ai.check(saved.id);
			next();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'AI settings not saved');
		} finally {
			saving = false;
		}
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
			disabled={saving || !catalog}
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
					spellcheck={false}
					class="h-9 font-mono text-xs"
					disabled={saving}
				/>
				{#if spec.base_url_hint}
					<p class="text-xs text-muted-foreground">{spec.base_url_hint}</p>
				{/if}
			</div>
		{/if}

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
					placeholder={keyStored ? (saved?.key_masked ?? '') : (spec?.key_hint ?? '')}
					autocomplete="off"
					spellcheck={false}
					class="h-9 pr-9 font-mono text-xs"
					disabled={saving}
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
			<ModelPicker
				id="ai-model"
				{provider}
				{request}
				bind:value={model}
				bind:selected={picked}
				disabled={saving}
			/>
		</div>

		<div>
			<LoadingButton
				variant="outline"
				size="sm"
				class="h-8 text-xs"
				loading={testing}
				loadingLabel="Testing"
				disabled={saving}
				onclick={() => handleTest()}
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
