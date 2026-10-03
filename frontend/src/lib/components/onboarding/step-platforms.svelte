<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import CheckIcon from '@lucide/svelte/icons/check';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import EmptyState from '$lib/components/empty-state.svelte';
	import NinjaIcon from '$lib/components/icons/ninja.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { apiKeysApi } from '$lib/api/api-keys';
	import { bountyProgramsApi } from '$lib/api/bounty-programs';
	import { SYNC_INTERVAL_LABELS } from '$lib/config/bounty-programs';
	import { getProviderIcon } from '$lib/config/icons';
	import { externalHref } from '$lib/utilities/links';
	import type { APIProvider, ProviderInfo } from '$lib/types/api-key';
	import type { BountySettings, PlatformCount } from '$lib/types/bounty-program';
	import type { StepProps } from '$lib/types/onboarding';

	let { next, setFooter }: StepProps = $props();

	interface Draft {
		username: string;
		token: string;
		reveal: boolean;
		connecting: boolean;
		error: string | null;
		result: string | null;
	}

	let settings = $state<BountySettings | null>(null);
	let providers = $state<ProviderInfo[]>([]);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let drafts = $state<Record<string, Draft>>({});
	let busy = $state(false);
	let savingInterval = $state(false);

	const connectable = $derived(
		(settings?.platforms ?? []).filter(
			(p) => p.api_provider && providers.some((i) => i.provider === p.api_provider)
		)
	);

	function providerOf(p: PlatformCount): ProviderInfo | undefined {
		return providers.find((i) => i.provider === p.api_provider);
	}

	function blank(): Draft {
		return { username: '', token: '', reveal: false, connecting: false, error: null, result: null };
	}

	async function load() {
		loading = true;
		try {
			[settings, providers] = await Promise.all([
				bountyProgramsApi.settings(),
				apiKeysApi.listProviders()
			]);
			for (const p of settings.platforms) drafts[p.platform] ??= blank();
			loadError = null;
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Platforms not loaded';
		} finally {
			loading = false;
		}
	}

	onMount(load);

	$effect(() => {
		setFooter({ onNext: handleNext, nextLabel: 'Continue', nextLoading: busy, canSkip: true });
	});

	function filled(p: PlatformCount): boolean {
		const d = drafts[p.platform];
		if (!d || p.configured || !d.token.trim()) return false;
		return !providerOf(p)?.requires_username || !!d.username.trim();
	}

	async function connect(p: PlatformCount): Promise<boolean> {
		const provider = providerOf(p);
		const d = drafts[p.platform];
		if (!provider || !d) return false;
		if (provider.requires_username && !d.username.trim()) {
			d.error = `${p.label} requires the API username.`;
			return false;
		}
		d.connecting = true;
		d.error = null;
		try {
			const key = await apiKeysApi.create({
				provider: provider.provider as APIProvider,
				key_value: d.token.trim(),
				...(provider.requires_username ? { key_meta: { username: d.username.trim() } } : {})
			});
			const test = await apiKeysApi.test(key.id);
			if (!test.success) {
				await apiKeysApi.delete(key.id).catch(() => {});
				d.error = test.message;
				return false;
			}
			d.result = test.message;
			d.token = '';
			await bountyProgramsApi.sync(true, p.platform).catch(() => {});
			settings = await bountyProgramsApi.settings();
			return true;
		} catch (e) {
			d.error = e instanceof Error ? e.message : `${p.label} not connected.`;
			return false;
		} finally {
			d.connecting = false;
		}
	}

	async function saveInterval(value: string) {
		savingInterval = true;
		try {
			settings = await bountyProgramsApi.saveSettings({ sync_interval: value });
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Sync interval not saved');
		} finally {
			savingInterval = false;
		}
	}

	async function handleNext() {
		busy = true;
		try {
			for (const p of connectable.filter(filled)) {
				if (!(await connect(p))) return;
			}
			next();
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	{#if loading}
		{#each [0, 1] as i (i)}
			<Skeleton class="h-36 w-full rounded-lg" />
		{/each}
	{:else if loadError}
		<EmptyState compact icon={NinjaIcon} title="Platforms not loaded" description={loadError} />
	{:else if settings}
		<div class="space-y-3">
			{#each connectable as p (p.platform)}
				{@const provider = providerOf(p)}
				{@const d = drafts[p.platform]}
				{@const Icon = getProviderIcon(provider?.icon ?? 'package')}
				<div class="rounded-lg border p-4">
					<div class="flex items-start gap-3">
						<div
							class="flex size-9 shrink-0 items-center justify-center rounded-lg border bg-muted"
						>
							<Icon class="size-[18px] text-muted-foreground" />
						</div>
						<div class="min-w-0 flex-1 space-y-3">
							<div class="space-y-0.5">
								<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
									<span class="text-sm font-medium">{p.label}</span>
									{#if !p.configured && provider}
										<a
											href={externalHref(provider.docs_url)}
											target="_blank"
											rel="noopener noreferrer"
											class="inline-flex items-center gap-1 text-xs text-primary"
										>
											Get API key
											<ExternalLinkIcon class="size-3" />
										</a>
									{/if}
								</div>
								<p class="text-xs text-muted-foreground">{p.note}</p>
							</div>

							{#if p.configured}
								<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
									<span class="inline-flex items-center gap-1 text-success">
										<CheckIcon class="size-3.5" />
										Connected
									</span>
									{#if p.programs > 0}
										<span class="text-muted-foreground tabular-nums">
											{p.programs.toLocaleString()} programs
											{#if p.private_programs > 0}
												· {p.private_programs.toLocaleString()} private
											{/if}
										</span>
									{:else}
										<span class="text-muted-foreground">Program sync started</span>
									{/if}
								</div>
								{#if d?.result}
									<p class="text-xs text-muted-foreground">{d.result}</p>
								{/if}
							{:else if d}
								<div class="grid gap-3 sm:grid-cols-2">
									{#if provider?.requires_username}
										<div class="space-y-1.5">
											<Label class="text-xs" for="user-{p.platform}">API username</Label>
											<Input
												id="user-{p.platform}"
												bind:value={d.username}
												disabled={d.connecting || busy}
												class="h-9 text-xs"
												autocomplete="off"
											/>
										</div>
									{/if}
									<div class="space-y-1.5 {provider?.requires_username ? '' : 'sm:col-span-2'}">
										<Label class="text-xs" for="token-{p.platform}">API token</Label>
										<div class="relative">
											<Input
												id="token-{p.platform}"
												type={d.reveal ? 'text' : 'password'}
												bind:value={d.token}
												disabled={d.connecting || busy}
												class="h-9 pr-9 text-xs"
												autocomplete="off"
											/>
											<button
												type="button"
												class="absolute top-1/2 right-2.5 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
												onclick={() => (d.reveal = !d.reveal)}
												aria-label={d.reveal ? 'Hide token' : 'Show token'}
											>
												{#if d.reveal}<EyeOffIcon class="size-4" />{:else}<EyeIcon
														class="size-4"
													/>{/if}
											</button>
										</div>
									</div>
								</div>
								<div class="flex flex-wrap items-center gap-3">
									<LoadingButton
										variant="outline"
										size="sm"
										class="h-8 text-xs"
										loading={d.connecting}
										loadingLabel="Connecting"
										disabled={!filled(p) || busy}
										onclick={() => connect(p)}
									>
										Connect
									</LoadingButton>
									{#if d.error}
										<span class="text-xs text-destructive">{d.error}</span>
									{/if}
								</div>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		</div>

		<div class="flex flex-wrap items-center justify-between gap-4 rounded-lg border px-4 py-3">
			<div class="flex min-w-0 flex-col gap-0.5">
				<span class="text-sm font-medium">Program sync</span>
				<span class="text-xs text-muted-foreground">Scope from connected platforms.</span>
			</div>
			<Select.Root
				type="single"
				value={settings.sync_interval}
				onValueChange={(v) => v && saveInterval(v)}
				disabled={savingInterval}
			>
				<Select.Trigger class="h-9 w-44 shrink-0 text-sm">
					{SYNC_INTERVAL_LABELS[settings.sync_interval] ?? settings.sync_interval}
				</Select.Trigger>
				<Select.Content>
					{#each Object.entries(SYNC_INTERVAL_LABELS) as [value, label] (value)}
						<Select.Item {value} {label}>{label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
	{/if}
</div>
