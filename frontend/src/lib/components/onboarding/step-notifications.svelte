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
	import BellIcon from '@lucide/svelte/icons/bell';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import CheckIcon from '@lucide/svelte/icons/check';
	import { notificationChannelsApi } from '$lib/api/notificationChannels';
	import {
		NOTIF_CATEGORIES,
		NOTIF_SEVERITIES,
		defaultNotificationPreference,
		type NotifProvider
	} from '$lib/types/notification-channel';
	import { ONBOARDING_NOTIFICATION_PROVIDERS as PROVIDERS } from '$lib/config/notification-providers';
	import type { StepProps } from '$lib/types/onboarding';
	import StepHeader from './step-header.svelte';
	import { SvelteSet } from 'svelte/reactivity';

	let { next, setFooter }: StepProps = $props();

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

	let drafts = $state<Record<NotifProvider, ChannelDraft>>({
		slack: blankDraft(),
		discord: blankDraft(),
		teams: blankDraft(),
		telegram: blankDraft(),
		email: blankDraft(),
		webhook: blankDraft(),
		custom: blankDraft()
	});

	let pref = $state(defaultNotificationPreference());
	let busy = $state(false);

	let severityLabel = $derived(
		NOTIF_SEVERITIES.find((s) => s.value === pref.min_severity)?.label ?? 'Everything'
	);
	let anyEnabled = $derived(PROVIDERS.some((m) => drafts[m.provider].enabled));

	$effect(() => {
		setFooter({ onNext: handleNext, nextLabel: 'Continue', nextLoading: busy, canSkip: true });
	});

	function isConfigured(p: NotifProvider): boolean {
		const meta = PROVIDERS.find((m) => m.provider === p);
		if (!meta) return false;
		const d = drafts[p];
		return meta.fields.every((f) => (d.config[f.key] ?? '').trim() !== '');
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
			toast.error('Fill in the channel details first');
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

	async function handleNext() {
		const pending = PROVIDERS.filter((m) => drafts[m.provider].enabled && isConfigured(m.provider));
		busy = true;
		try {
			for (const meta of pending) {
				const d = drafts[meta.provider];
				if (d.createdId) {
					await notificationChannelsApi.update(d.createdId, { events: pref });
				} else {
					await notificationChannelsApi.create({
						name: meta.name,
						provider: meta.provider,
						config: buildConfig(meta.provider),
						events: pref
					});
				}
			}
			next();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to save notification channels');
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	<StepHeader
		icon={BellIcon}
		title="Connect notifications"
		description="Route scan and recon events to Slack, Discord, Telegram, email, and more. Skip and add channels later in Settings."
	/>

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
									Testing...
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
	</div>

	{#if anyEnabled}
		<Card.Root>
			<Card.Content class="space-y-4 p-5">
				<div class="space-y-2">
					<Label class="text-xs">Notify me about</Label>
					<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
						{#each NOTIF_CATEGORIES as cat (cat.value)}
							<Label
								class="flex cursor-pointer items-start gap-2 rounded-md border border-input px-2.5 py-2 text-xs data-[active=true]:border-primary data-[active=true]:bg-muted"
								data-active={pref.types.includes(cat.value)}
							>
								<Checkbox
									checked={pref.types.includes(cat.value)}
									onCheckedChange={(v) => toggleCategory(cat.value, v === true)}
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
					<Select.Root type="single" value={pref.min_severity} onValueChange={(v) => (pref = { ...pref, min_severity: v ?? 'info' })}>
						<Select.Trigger class="h-9 w-full text-sm sm:max-w-xs">{severityLabel}</Select.Trigger>
						<Select.Content>
							{#each NOTIF_SEVERITIES as s (s.value)}
								<Select.Item value={s.value} label={s.label}>{s.label}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
					<p class="text-xs text-muted-foreground">Applies to every channel you connect here. Fine-tune per channel in Settings.</p>
				</div>
			</Card.Content>
		</Card.Root>
	{/if}
</div>
