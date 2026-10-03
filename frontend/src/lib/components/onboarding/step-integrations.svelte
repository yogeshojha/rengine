<script lang="ts">
	import { onMount } from 'svelte';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import EmptyState from '$lib/components/empty-state.svelte';
	import FormField from '$lib/components/form-field.svelte';
	import { apiKeysApi } from '$lib/api/api-keys';
	import type { ProviderInfo } from '$lib/types/api-key';
	import { getProviderIcon } from '$lib/config/icons';
	import { RECON_GROUPS, type ProviderGroup } from '$lib/config/api-keys';
	import { plural } from '$lib/utilities/strings';
	import { externalHref } from '$lib/utilities/links';
	import { toast } from 'svelte-sonner';
	import type { StepProps } from '$lib/types/onboarding';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import PlugIcon from '@lucide/svelte/icons/plug';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { Button } from '$lib/components/ui/button/index.js';

	let { setFooter, next }: StepProps = $props();

	let providers = $state<ProviderInfo[]>([]);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let keys = $state<Record<string, string>>({});
	let usernames = $state<Record<string, string>>({});
	let reveal = $state<Record<string, boolean>>({});
	let busy = $state(false);

	const groups = $derived(
		RECON_GROUPS.map((group) => ({
			group,
			items: providers.filter((p) => p.group === group)
		})).filter((g) => g.items.length > 0)
	);

	async function load() {
		loading = true;
		try {
			providers = (await apiKeysApi.listProviders()).filter(
				(p) => !p.configured && RECON_GROUPS.includes(p.group as ProviderGroup)
			);
			loadError = null;
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'API keys not loaded';
		} finally {
			loading = false;
		}
	}

	onMount(load);

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
			if (saved > 0) toast.success(`${plural(saved, 'API key')} saved`);
			next();
		} finally {
			busy = false;
		}
	}
</script>

<div class="space-y-6">
	{#if loading}
		<div class="space-y-3">
			{#each [0, 1, 2] as i (i)}
				<Skeleton class="h-28 w-full rounded-lg" />
			{/each}
		</div>
	{:else if loadError}
		<EmptyState
			compact
			icon={TriangleAlertIcon}
			title="API keys not loaded"
			description={loadError}
		>
			<Button size="sm" variant="outline" onclick={() => load()}>Retry</Button>
		</EmptyState>
	{:else if providers.length === 0}
		<EmptyState compact icon={PlugIcon} title="API keys saved" />
	{:else}
		{#each groups as g (g.group)}
			<section class="space-y-2">
				<h3 class="text-sm font-medium">{g.items[0].group_label}</h3>
				<div class="space-y-3">
					{#each g.items as p (p.provider)}
						{@const Icon = getProviderIcon(p.icon)}
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
											<span class="text-sm font-medium">{p.name}</span>
											<a
												href={externalHref(p.docs_url)}
												target="_blank"
												rel="noopener noreferrer"
												class="inline-flex items-center gap-1 text-xs text-primary transition-colors hover:text-primary/80"
											>
												Get API key
												<ExternalLinkIcon class="size-3" />
											</a>
										</div>
										<p class="text-xs text-muted-foreground">{p.description}</p>
									</div>
									<div class="grid gap-4 sm:grid-cols-2">
										{#if p.requires_username}
											<FormField label="API username">
												{#snippet children({ id })}
													<Input
														{id}
														bind:value={usernames[p.provider]}
														disabled={busy}
														class="h-9 text-xs"
														autocomplete="off"
													/>
												{/snippet}
											</FormField>
										{/if}
										<FormField
											label="API key"
											class={p.requires_username ? undefined : 'sm:col-span-2'}
										>
											{#snippet children({ id })}
												<div class="relative">
													<Input
														{id}
														type={reveal[p.provider] ? 'text' : 'password'}
														bind:value={keys[p.provider]}
														disabled={busy}
														class="h-9 pr-9 text-xs"
														autocomplete="off"
													/>
													<button
														type="button"
														class="absolute top-1/2 right-2.5 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
														onclick={() => (reveal[p.provider] = !reveal[p.provider])}
														aria-label={reveal[p.provider] ? 'Hide key' : 'Show key'}
													>
														{#if reveal[p.provider]}<EyeOffIcon class="size-4" />{:else}<EyeIcon
																class="size-4"
															/>{/if}
													</button>
												</div>
											{/snippet}
										</FormField>
									</div>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</section>
		{/each}
	{/if}
</div>
