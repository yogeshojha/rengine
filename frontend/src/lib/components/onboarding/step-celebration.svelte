<script lang="ts">
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import { MODE_LABELS, coerceInstanceMode } from '$lib/config/capabilities';
	import { onboardingApi } from '$lib/api/onboarding';
	import { onboardingStore } from '$lib/stores/onboarding.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { toast } from 'svelte-sonner';
	import CheckIcon from '@lucide/svelte/icons/check';
	import PartyPopperIcon from '@lucide/svelte/icons/party-popper';
	import ArrowRightIcon from '@lucide/svelte/icons/arrow-right';
	import SettingsIcon from '@lucide/svelte/icons/settings';
	import { fireConfetti } from './confetti';
	import StepHeader from './step-header.svelte';
	import type { StepProps } from '$lib/types/onboarding';

	let { setFooter }: StepProps = $props();

	let finishing = $state(true);

	let done = $derived.by(() => {
		const status = onboardingStore.status;
		const items: string[] = ['Instance secured'];
		if (status?.mode) {
			items.push(`Mode set to ${MODE_LABELS[coerceInstanceMode(status.mode)]}`);
		}
		const s = status?.summary;
		if (s && s.integrations > 0) {
			items.push(`${s.integrations} integration${s.integrations === 1 ? '' : 's'} configured`);
		}
		if (s && s.proxies > 0) {
			items.push(`${s.proxies} prox${s.proxies === 1 ? 'y' : 'ies'} configured`);
		}
		if (s?.ai_enabled) items.push('AI assistance enabled');
		if (s && s.channels > 0) {
			items.push(`${s.channels} notification channel${s.channels === 1 ? '' : 's'}`);
		}
		items.push('First project created');
		return items;
	});

	let optional = $derived.by(() => {
		const s = onboardingStore.status?.summary;
		if (!s) return [] as { label: string; href: string }[];
		const items: { label: string; href: string }[] = [];
		if (s.integrations === 0) items.push({ label: 'Integrations', href: ROUTES.settings() });
		if (s.proxies === 0) items.push({ label: 'Proxies', href: ROUTES.settings() });
		if (!s.ai_enabled) items.push({ label: 'AI assistance', href: ROUTES.settings() });
		if (s.channels === 0) items.push({ label: 'Notifications', href: ROUTES.settings() });
		return items;
	});

	$effect(() => setFooter({ onNext: () => {}, hidden: true }));

	$effect(() => {
		(async () => {
			try {
				await onboardingApi.complete();
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to finalize onboarding');
			}
			fireConfetti();
			await Promise.allSettled([projectsStore.refresh(), onboardingStore.refresh()]);
			finishing = false;
		})();
	});

	function launch() {
		goto(ROUTES.dashboard);
	}
</script>

<div class="space-y-6 text-center">
	<div class="flex flex-col items-center">
		<StepHeader
			icon={PartyPopperIcon}
			title="You're all set"
			description="reNgine is configured and ready."
		/>
	</div>

	<ul class="mx-auto max-w-sm space-y-2.5 text-left">
		{#each done as label (label)}
			<li class="flex items-center gap-3 text-sm">
				<span
					class="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground"
				>
					<CheckIcon class="size-3" />
				</span>
				<span class="text-foreground">{label}</span>
			</li>
		{/each}
	</ul>

	{#if optional.length}
		<div class="mx-auto max-w-sm space-y-2.5 text-left">
			<p class="text-xs text-muted-foreground">Optional — set these up anytime in Settings.</p>
			<ul class="space-y-2.5">
				{#each optional as item (item.label)}
					<li>
						<a
							href={item.href}
							class="flex items-center gap-3 text-sm text-muted-foreground transition-colors hover:text-foreground"
						>
							<span
								class="flex size-5 shrink-0 items-center justify-center rounded-full border border-dashed border-border"
							>
								<SettingsIcon class="size-3" />
							</span>
							<span>{item.label} — add later</span>
							<ArrowRightIcon class="ml-auto size-3.5 opacity-60" />
						</a>
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<div class="flex justify-center pt-2">
		<Button size="lg" class="gap-2" onclick={launch} disabled={finishing}>
			{#if finishing}
				<Spinner class="size-4" />
				Finishing up…
			{:else}
				Launch reNgine
				<ArrowRightIcon class="size-4" />
			{/if}
		</Button>
	</div>
</div>
