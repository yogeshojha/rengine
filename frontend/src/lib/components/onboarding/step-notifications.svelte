<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Switch } from '$lib/components/ui/switch/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { toast } from 'svelte-sonner';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import CheckIcon from '@lucide/svelte/icons/check';
	import InfoIcon from '@lucide/svelte/icons/info';
	import { notificationChannelsApi } from '$lib/api/notificationChannels';
	import {
		defaultNotificationPreference,
		type NotifProvider
	} from '$lib/types/notification-channel';
	import {
		ONBOARDING_NOTIFICATION_PROVIDERS as PROVIDERS,
		SHARED_BOT_FIELD,
		SHARED_BOT_KEY,
		SHARED_BOT_PROVIDER
	} from '$lib/config/notification-providers';
	import {
		CHANNEL_LEVELS,
		DEFAULT_CHANNEL_LEVEL,
		channelEventsFor
	} from '$lib/config/notification-events';
	import { apiKeysApi } from '$lib/api/api-keys';
	import type { StepProps } from '$lib/types/onboarding';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { SvelteSet } from 'svelte/reactivity';

	let { next, setFooter }: StepProps = $props();
	const categories = $derived(channelEventsFor((c) => capabilitiesStore.has(c)));

	interface ChannelDraft {
		enabled: boolean;
		config: Record<string, string>;
		createdId: string | null;
		testing: boolean;
		tested: boolean;
	}

	function blankDraft(): ChannelDraft {
		return { enabled: false, config: {}, createdId: null, testing: false, tested: false };
	}

	let drafts = $state(
		Object.fromEntries(PROVIDERS.map((m) => [m.provider, blankDraft()])) as Record<
			NotifProvider,
			ChannelDraft
		>
	);

	let pref = $state(defaultNotificationPreference());
	let busy = $state(false);

	let severityLabel = $derived(CHANNEL_LEVELS.find((s) => s.value === pref.min_severity)?.label);
	let anyEnabled = $derived(PROVIDERS.some((m) => drafts[m.provider].enabled));

	$effect(() => {
		setFooter({ onNext: handleNext, nextLabel: 'Continue', nextLoading: busy, canSkip: true });
	});

	function isConfigured(p: NotifProvider): boolean {
		const meta = PROVIDERS.find((m) => m.provider === p);
		if (!meta) return false;
		const d = drafts[p];
		return meta.fields.every((f) => !f.required || (d.config[f.key] ?? '').trim() !== '');
	}

	function setField(p: NotifProvider, key: string, value: string) {
		const d = drafts[p];
		d.config = { ...d.config, [key]: value };
		d.createdId = null;
		d.tested = false;
	}

	function toggleCategory(value: string, on: boolean) {
		const set = new SvelteSet(pref.types);
		if (on) set.add(value);
		else set.delete(value);
		pref = { ...pref, types: [...set] };
	}

	function buildConfig(p: NotifProvider): Record<string, string> {
		const meta = PROVIDERS.find((m) => m.provider === p);
		const out: Record<string, string> = {};
		for (const f of meta?.fields ?? []) out[f.key] = (drafts[p].config[f.key] ?? '').trim();
		return out;
	}

	async function handleTest(p: NotifProvider) {
		if (!isConfigured(p)) {
			toast.error('Fill in the channel fields');
			return;
		}
		const d = drafts[p];
		d.testing = true;
		try {
			const result = await notificationChannelsApi.testConfig({
				provider: p,
				config: buildConfig(p)
			});
			d.tested = result.success;
			if (result.success) toast.success(result.message);
			else toast.error(result.message);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Test failed');
		} finally {
			d.testing = false;
		}
	}

	async function channelConfig(p: NotifProvider): Promise<Record<string, string>> {
		const config = buildConfig(p);
		const token = config[SHARED_BOT_FIELD];
		if (p !== SHARED_BOT_PROVIDER || !token) return config;
		await apiKeysApi.upsert(SHARED_BOT_KEY, token);
		return { ...config, [SHARED_BOT_FIELD]: '' };
	}

	async function handleNext() {
		const pending = PROVIDERS.filter((m) => drafts[m.provider].enabled);
		const incomplete = pending.find((m) => !isConfigured(m.provider));
		if (incomplete) {
			toast.error(`${incomplete.name} fields are empty`);
			return;
		}
		busy = true;
		try {
			for (const meta of pending) {
				const d = drafts[meta.provider];
				if (d.createdId) {
					await notificationChannelsApi.update(d.createdId, { events: pref });
				} else {
					const created = await notificationChannelsApi.create({
						name: meta.name,
						provider: meta.provider,
						config: await channelConfig(meta.provider),
						events: pref
					});
					d.createdId = created.id;
				}
			}
			next();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Notification channels not saved');
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	<div class="space-y-4">
		{#each PROVIDERS as meta (meta.provider)}
			{@const d = drafts[meta.provider]}
			{@const Icon = meta.icon}
			<Card.Root class={d.enabled ? 'ring-1 ring-border' : 'border-dashed'}>
				<Card.Content class="p-5">
					<div class="flex items-center justify-between gap-3">
						<div class="flex items-center gap-3">
							<div
								class="flex size-9 shrink-0 items-center justify-center rounded-lg border bg-muted {d.enabled
									? 'border-primary text-foreground'
									: 'text-muted-foreground'}"
							>
								<Icon class="size-[18px]" />
							</div>
							<h4 class="text-sm font-medium">{meta.name}</h4>
						</div>
						<Switch
							checked={d.enabled}
							onCheckedChange={(v) => (drafts[meta.provider].enabled = v)}
							disabled={busy}
						/>
					</div>

					{#if d.enabled}
						<Separator class="my-4" />
						<div class="space-y-3">
							{#each meta.fields as field (field.key)}
								<div class="space-y-1.5">
									<Label class="text-xs" for="{meta.provider}-{field.key}">{field.label}</Label>
									<Input
										id="{meta.provider}-{field.key}"
										value={d.config[field.key] ?? ''}
										placeholder={field.placeholder}
										autocomplete="off"
										class="h-9 font-mono text-xs"
										disabled={busy}
										oninput={(e) => setField(meta.provider, field.key, e.currentTarget.value)}
									/>
								</div>
							{/each}
						</div>
						{#if meta.provider === SHARED_BOT_PROVIDER}
							<p class="mt-3 text-xs text-muted-foreground">
								The bot token is saved as the {meta.name} API key. Remote control uses the same bot.
							</p>
						{/if}
						<div class="mt-4">
							<Button
								variant="outline"
								size="sm"
								class="h-8 text-xs"
								disabled={d.testing || busy || !isConfigured(meta.provider)}
								onclick={() => handleTest(meta.provider)}
							>
								{#if d.testing}
									<Spinner class="mr-1.5 size-4" />
									Testing…
								{:else if d.tested}
									<CheckIcon class="mr-1.5 size-4" />
									Tested
								{:else}
									<FlaskConicalIcon class="mr-1.5 size-4" />
									Send test
								{/if}
							</Button>
						</div>
					{/if}
				</Card.Content>
			</Card.Root>
		{/each}

		<p class="flex items-start gap-2 pt-1 text-xs text-muted-foreground">
			<InfoIcon class="mt-px size-3.5 shrink-0" />
			<span>Email, Microsoft Teams and Apprise URLs can be added in Settings.</span>
		</p>
	</div>

	{#if anyEnabled}
		<Card.Root>
			<Card.Content class="space-y-4 p-5">
				<div class="space-y-2">
					<Label class="text-xs">Event categories</Label>
					<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
						{#each categories as cat (cat.type)}
							<Label
								class="flex cursor-pointer items-start gap-2 rounded-md border border-input px-2.5 py-2 text-xs data-[active=true]:border-primary data-[active=true]:bg-muted"
								data-active={pref.types.includes(cat.type)}
							>
								<Checkbox
									checked={pref.types.includes(cat.type)}
									onCheckedChange={(v) => toggleCategory(cat.type, v === true)}
									class="mt-0.5"
								/>
								<span class="min-w-0">
									<span class="block font-medium">{cat.label}</span>
									<span class="block text-muted-foreground">{cat.hint}</span>
								</span>
							</Label>
						{/each}
					</div>
				</div>
				<div class="space-y-1.5">
					<Label class="text-xs">Minimum severity</Label>
					<Select.Root
						type="single"
						value={pref.min_severity}
						onValueChange={(v) => (pref = { ...pref, min_severity: v ?? DEFAULT_CHANNEL_LEVEL })}
					>
						<Select.Trigger class="h-9 w-full text-sm sm:max-w-xs">{severityLabel}</Select.Trigger>
						<Select.Content>
							{#each CHANNEL_LEVELS as s (s.value)}
								<Select.Item value={s.value} label={s.label}>{s.label}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
					<p class="text-xs text-muted-foreground">
						Applies to every channel above. Adjustable per channel in Settings.
					</p>
				</div>
			</Card.Content>
		</Card.Root>
	{/if}
</div>
