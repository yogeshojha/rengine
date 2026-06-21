<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as RadioGroup from '$lib/components/ui/radio-group/index.js';
	import * as Alert from '$lib/components/ui/alert/index.js';
	import { toast } from 'svelte-sonner';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import { instanceSettingsApi } from '$lib/api/instanceSettings';
	import { AI_PROVIDERS as PROVIDERS, AI_FEATURES as FEATURES } from '$lib/config/ai';
	import StepHeader from './step-header.svelte';
	import type { StepProps } from '$lib/types/onboarding';

	let { next, setFooter }: StepProps = $props();

	let enabled = $state(false);
	let provider = $state<string>('openai');
	let apiKey = $state('');
	let model = $state('');
	let showKey = $state(false);
	let features = $state<Record<string, boolean>>({
		vuln_descriptions: true,
		impact_assessment: true,
		remediation: true,
		auto_report: false
	});

	let testing = $state(false);
	let busy = $state(false);

	$effect(() => {
		setFooter({ onNext: handleNext, nextLabel: 'Continue', nextLoading: busy, canSkip: true });
	});

	function selectProvider(v: string) {
		provider = v;
		const meta = PROVIDERS.find((p) => p.value === v);
		if (meta && !model.trim()) model = meta.model;
	}

	let modelPlaceholder = $derived(PROVIDERS.find((p) => p.value === provider)?.model ?? 'model name');

	async function handleTest() {
		if (!apiKey.trim()) {
			toast.error('Enter an API key to test the connection');
			return;
		}
		testing = true;
		try {
			const result = await instanceSettingsApi.testAi({
				provider,
				model: model.trim() || undefined,
				api_key: apiKey.trim()
			});
			if (result.success) toast.success(result.message);
			else toast.error(result.message);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Test failed');
		} finally {
			testing = false;
		}
	}

	async function handleNext() {
		if (!enabled) {
			busy = true;
			try {
				await instanceSettingsApi.update({ ai_enabled: false });
				next();
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to save AI settings');
			} finally {
				busy = false;
			}
			return;
		}

		if (!apiKey.trim()) {
			toast.error('An API key is required to enable AI analysis');
			return;
		}

		busy = true;
		try {
			await instanceSettingsApi.update({
				ai_enabled: true,
				ai_provider: provider,
				ai_model: model.trim() || null,
				ai_api_key: apiKey.trim(),
				ai_features: features
			});
			next();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to save AI settings');
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	<StepHeader
		icon={SparklesIcon}
		title="AI-powered analysis"
		description="Use an LLM to summarize findings and draft remediation. Scan data is sent to the provider you choose."
	/>

	<div class="flex items-center justify-between rounded-lg border px-4 py-3">
		<div class="space-y-0.5">
			<Label class="text-sm font-medium">Enable AI-powered analysis</Label>
			<p class="text-xs text-muted-foreground">Connect an external LLM provider.</p>
		</div>
		<Switch checked={enabled} onCheckedChange={(v) => (enabled = v)} disabled={busy} />
	</div>

	{#if enabled}
		<Alert.Root variant="destructive">
			<TriangleAlertIcon />
			<Alert.Title>Scan data leaves your instance</Alert.Title>
			<Alert.Description>
				Enabling AI sends scan data (targets, findings, and context) to your chosen external provider
				for processing. Do not enable this on air-gapped or sensitive deployments.
			</Alert.Description>
		</Alert.Root>

		<div class="space-y-2">
			<Label class="text-xs">Provider</Label>
			<RadioGroup.Root
				value={provider}
				onValueChange={selectProvider}
				class="grid grid-cols-2 gap-2 sm:grid-cols-4"
			>
				{#each PROVIDERS as p (p.value)}
					<Label
						class="flex cursor-pointer items-center gap-2 rounded-md border border-input bg-transparent px-3 py-2 text-sm data-[active=true]:border-primary data-[active=true]:bg-muted"
						data-active={provider === p.value}
					>
						<RadioGroup.Item value={p.value} />
						<span class="truncate">{p.name}</span>
					</Label>
				{/each}
			</RadioGroup.Root>
		</div>

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
			<div class="space-y-1.5">
				<Label class="text-xs" for="ai-key">API key</Label>
				<div class="relative">
					<Input
						id="ai-key"
						type={showKey ? 'text' : 'password'}
						bind:value={apiKey}
						placeholder="Paste your API key"
						autocomplete="off"
						class="h-9 pr-9 font-mono text-xs"
						disabled={busy}
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
				<Input
					id="ai-model"
					bind:value={model}
					placeholder={modelPlaceholder}
					autocomplete="off"
					class="h-9 font-mono text-xs"
					disabled={busy}
				/>
			</div>
		</div>

		<div>
			<Button
				variant="outline"
				size="sm"
				class="h-8 text-xs"
				disabled={testing || busy || !apiKey.trim()}
				onclick={handleTest}
			>
				{#if testing}
					<Spinner class="mr-1.5 size-3" />
					Testing...
				{:else}
					<FlaskConicalIcon class="mr-1.5 size-3" />
					Test connection
				{/if}
			</Button>
		</div>

		<Separator />

		<div class="space-y-3">
			<Label class="text-xs">Features</Label>
			<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
				{#each FEATURES as f (f.key)}
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
							<span class="block text-xs text-muted-foreground">{f.hint}</span>
						</span>
					</Label>
				{/each}
			</div>
		</div>
	{/if}
</div>
