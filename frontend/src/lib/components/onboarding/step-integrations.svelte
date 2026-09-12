<script lang="ts">
	import { Input } from '$lib/components/ui/input/index.js';
	import { Label } from '$lib/components/ui/label/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { apiKeysApi } from '$lib/api/api-keys';
	import { APIProvider } from '$lib/types/api-key';
	import { toast } from 'svelte-sonner';
	import type { StepProps } from '$lib/types/onboarding';
	import { Capability, modeHas } from '$lib/config/capabilities';
	import type { Component } from 'svelte';
	import RadarIcon from '@lucide/svelte/icons/radar';
	import GlobeIcon from '@lucide/svelte/icons/globe';
	import RouteIcon from '@lucide/svelte/icons/route';
	import ShieldIcon from '@lucide/svelte/icons/shield';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';

	let { data, next, setFooter }: StepProps = $props();

	interface ProviderCard {
		provider: APIProvider;
		name: string;
		desc: string;
		docs: string;
		docsLabel: string;
		icon: Component;
	}

	const SIMPLE: ProviderCard[] = [
		{
			provider: APIProvider.CHAOS,
			name: 'Chaos',
			desc: 'The ProjectDiscovery passive subdomain dataset.',
			docs: 'https://cloud.projectdiscovery.io',
			docsLabel: 'Get API key',
			icon: RadarIcon
		},
		{
			provider: APIProvider.NETLAS,
			name: 'Netlas',
			desc: 'Internet-wide host and certificate intelligence.',
			docs: 'https://netlas.io',
			docsLabel: 'Get API key',
			icon: GlobeIcon
		},
		{
			provider: APIProvider.SECURITYTRAILS,
			name: 'SecurityTrails',
			desc: 'Historical DNS and domain registration records.',
			docs: 'https://securitytrails.com',
			docsLabel: 'Get API key',
			icon: RouteIcon
		}
	];

	const BOUNTY: ProviderCard[] = [
		{
			provider: APIProvider.INTIGRITI,
			name: 'Intigriti',
			desc: 'Import programs and their scope from Intigriti, including invite-only programs.',
			docs: 'https://app.intigriti.com/researcher/personal-access-tokens',
			docsLabel: 'Create a token',
			icon: ShieldIcon
		}
	];

	const showBountyPlatforms = $derived(modeHas(data.mode, Capability.BOUNTY_PLATFORMS));
	const cards = $derived(showBountyPlatforms ? [...SIMPLE, ...BOUNTY] : SIMPLE);

	let keys = $state<Record<string, string>>({
		[APIProvider.CHAOS]: '',
		[APIProvider.NETLAS]: '',
		[APIProvider.SECURITYTRAILS]: '',
		[APIProvider.INTIGRITI]: ''
	});
	let reveal = $state<Record<string, boolean>>({});

	let h1Username = $state('');
	let h1Token = $state('');
	let h1Reveal = $state(false);

	let busy = $state(false);

	$effect(() => {
		setFooter({ onNext: handleNext, nextLabel: 'Continue', nextLoading: busy, canSkip: true });
	});

	function isAlreadyExists(e: unknown): boolean {
		const msg = e instanceof Error ? e.message.toLowerCase() : '';
		return msg.includes('already') || msg.includes('exists') || msg.includes('409');
	}

	async function createKey(
		provider: APIProvider,
		keyValue: string,
		keyMeta?: Record<string, unknown>
	): Promise<boolean> {
		try {
			await apiKeysApi.create({ provider, key_value: keyValue, key_meta: keyMeta ?? null });
			return true;
		} catch (e) {
			if (isAlreadyExists(e)) return true;
			toast.error(e instanceof Error ? e.message : `${provider} key not saved`);
			return false;
		}
	}

	async function handleNext() {
		busy = true;
		try {
			let saved = 0;
			let ok = true;

			for (const p of cards) {
				const v = (keys[p.provider] ?? '').trim();
				if (!v) continue;
				if (await createKey(p.provider, v)) saved++;
				else ok = false;
			}

			if (showBountyPlatforms && h1Token.trim()) {
				const meta = h1Username.trim() ? { username: h1Username.trim() } : undefined;
				if (await createKey(APIProvider.HACKERONE, h1Token.trim(), meta)) saved++;
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

<div class="space-y-6">
	<div class="space-y-3">
		{#each cards as p (p.provider)}
			{@const Icon = p.icon}
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
										href={p.docs}
										target="_blank"
										rel="noopener noreferrer"
										class="inline-flex items-center gap-1 text-xs text-primary hover:underline"
									>
										{p.docsLabel}
										<ExternalLinkIcon class="size-4" />
									</a>
								</div>
								<p class="text-xs text-muted-foreground">{p.desc}</p>
							</div>
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

		{#if showBountyPlatforms}
			<Card.Root>
				<Card.Content class="p-4">
					<div class="flex items-start gap-3">
						<div
							class="flex size-9 shrink-0 items-center justify-center rounded-lg border bg-muted"
						>
							<ShieldIcon class="size-[18px] text-muted-foreground" />
						</div>
						<div class="min-w-0 flex-1 space-y-3">
							<div class="space-y-0.5">
								<div class="flex items-center gap-2">
									<span class="text-sm font-medium">HackerOne</span>
									<a
										href="https://api.hackerone.com"
										target="_blank"
										rel="noopener noreferrer"
										class="inline-flex items-center gap-1 text-xs text-primary hover:underline"
									>
										Get API key <ExternalLinkIcon class="size-4" />
									</a>
								</div>
								<p class="text-xs text-muted-foreground">
									Import programs and their scope from HackerOne.
								</p>
							</div>
							<div class="space-y-2">
								<div class="space-y-1.5">
									<Label class="text-xs">API username</Label>
									<Input
										bind:value={h1Username}
										placeholder="username"
										disabled={busy}
										class="h-9 text-xs"
										autocomplete="off"
									/>
								</div>
								<div class="space-y-1.5">
									<Label class="text-xs">API token</Label>
									<div class="relative">
										<Input
											type={h1Reveal ? 'text' : 'password'}
											bind:value={h1Token}
											placeholder="Paste the API token"
											disabled={busy}
											class="h-9 pr-9 text-xs"
											autocomplete="off"
										/>
										<button
											type="button"
											class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
											onclick={() => (h1Reveal = !h1Reveal)}
											aria-label="Toggle visibility"
										>
											{#if h1Reveal}<EyeOffIcon class="size-4" />{:else}<EyeIcon
													class="size-4"
												/>{/if}
										</button>
									</div>
								</div>
							</div>
						</div>
					</div>
				</Card.Content>
			</Card.Root>
		{/if}
	</div>
</div>
