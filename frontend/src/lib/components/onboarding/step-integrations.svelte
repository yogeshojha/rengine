<script lang="ts">
	import { onMount } from 'svelte';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { apiKeysApi } from '$lib/api/api-keys';
	import type { ProviderInfo } from '$lib/types/api-key';
	import { getProviderIcon } from '$lib/config/icons';
	import { toast } from 'svelte-sonner';
	import type { StepProps } from '$lib/types/onboarding';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import PlugIcon from '@lucide/svelte/icons/plug';

	let { setFooter, next }: StepProps = $props();

	let providers = $state<ProviderInfo[]>([]);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let keys = $state<Record<string, string>>({});
	let usernames = $state<Record<string, string>>({});
	let reveal = $state<Record<string, boolean>>({});
	let busy = $state(false);

	onMount(async () => {
		try {
			providers = (await apiKeysApi.listProviders()).filter((p) => !p.configured);
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Integrations not loaded';
		} finally {
			loading = false;
		}
	});

	$effect(() => {
		setFooter({ onNext: handleNext, nextLabel: 'Continue', nextLoading: busy, canSkip: true });
	});

	function isAlreadyExists(e: unknown): boolean {
		const msg = e instanceof Error ? e.message.toLowerCase() : '';
		return msg.includes('already') || msg.includes('exists') || msg.includes('409');
	}

	async function createKey(p: ProviderInfo, keyValue: string): Promise<boolean> {
		const username = (usernames[p.provider] ?? '').trim();
		try {
			await apiKeysApi.create({
				provider: p.provider,
				key_value: keyValue,
				...(p.requires_username && username ? { key_meta: { username } } : {})
			});
			return true;
		} catch (e) {
			if (isAlreadyExists(e)) return true;
			toast.error(e instanceof Error ? e.message : `${p.name} key not saved`);
			return false;
		}
	}

	async function handleNext() {
		busy = true;
		try {
			let saved = 0;
			let ok = true;
			for (const p of providers) {
				const v = (keys[p.provider] ?? '').trim();
				if (!v) continue;
				if (p.requires_username && !(usernames[p.provider] ?? '').trim()) {
					toast.error(`${p.name} requires a username`);
					ok = false;
					continue;
				}
				if (await createKey(p, v)) saved++;
				else ok = false;
			}
			if (!ok) return;
			if (saved > 0) toast.success(`${saved} integration${saved > 1 ? 's' : ''} connected`);
			next();
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-3">
	{#if loading}
		{#each [0, 1, 2] as i (i)}
			<Skeleton class="h-28 w-full rounded-xl" />
		{/each}
	{:else if loadError}
		<EmptyState compact icon={PlugIcon} title="Integrations not loaded" description={loadError} />
	{:else if providers.length === 0}
		<EmptyState compact icon={PlugIcon} title="Every integration is already connected" />
	{:else}
		{#each providers as p (p.provider)}
			{@const Icon = getProviderIcon(p.icon)}
			<Card.Root>
				<Card.Content class="p-4">
					<div class="flex items-start gap-3">
						<div
							class="flex size-9 shrink-0 items-center justify-center rounded-lg border bg-muted"
						>
							<Icon class="size-[18px] text-muted-foreground" />
						</div>
						<div class="min-w-0 flex-1 space-y-3">
							<div class="space-y-0.5">
								<div class="flex items-center gap-2">
									<span class="text-sm font-medium">{p.name}</span>
									<a
										href={p.docs_url}
										target="_blank"
										rel="noopener noreferrer"
										class="inline-flex items-center gap-1 text-xs text-primary hover:underline"
									>
										Get API key
										<ExternalLinkIcon class="size-4" />
									</a>
								</div>
								<p class="text-xs text-muted-foreground">{p.description}</p>
							</div>
							{#if p.requires_username}
								<div class="space-y-1.5">
									<Label class="text-xs" for="user-{p.provider}">API username</Label>
									<Input
										id="user-{p.provider}"
										bind:value={usernames[p.provider]}
										placeholder="username"
										disabled={busy}
										class="h-9 text-xs"
										autocomplete="off"
									/>
								</div>
							{/if}
							<div class="relative">
								<Input
									type={reveal[p.provider] ? 'text' : 'password'}
									bind:value={keys[p.provider]}
									placeholder="Paste the API key"
									disabled={busy}
									class="h-9 pr-9 text-xs"
									autocomplete="off"
								/>
								<button
									type="button"
									class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
									onclick={() => (reveal[p.provider] = !reveal[p.provider])}
									aria-label="Toggle visibility"
								>
									{#if reveal[p.provider]}<EyeOffIcon class="size-4" />{:else}<EyeIcon
											class="size-4"
										/>{/if}
								</button>
							</div>
						</div>
					</div>
				</Card.Content>
			</Card.Root>
		{/each}
	{/if}
</div>
