<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import { Capability, MODE_LABELS, coerceInstanceMode, modeHas } from '$lib/config/capabilities';
	import { OAST_MODE_LABELS, OastMode } from '$lib/config/oast';
	import { FEED_STATUS_TONE, FeedStatus } from '$lib/config/threat-intel';
	import { datasetsApi } from '$lib/api/datasets';
	import { onboardingApi } from '$lib/api/onboarding';
	import { onboardingStore } from '$lib/stores/onboarding.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { toast } from 'svelte-sonner';
	import CheckIcon from '@lucide/svelte/icons/check';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import ArrowRightIcon from '@lucide/svelte/icons/arrow-right';
	import SettingsIcon from '@lucide/svelte/icons/settings';
	import StepHeader from './step-header.svelte';
	import { plural } from '$lib/utilities/strings';
	import type { DatasetRead } from '$lib/types/dataset';
	import type { StepProps } from '$lib/types/onboarding';

	let { setFooter }: StepProps = $props();

	interface LinkItem {
		label: string;
		detail?: string;
		href: string;
	}

	let finishing = $state(true);
	let pending = $state<DatasetRead[]>([]);

	let done = $derived.by(() => {
		const status = onboardingStore.status;
		const items: string[] = ['Instance settings saved'];
		if (status?.mode) {
			items.push(`Mode set to ${MODE_LABELS[coerceInstanceMode(status.mode)]}`);
		}
		const s = status?.summary;
		if (s && s.integrations > 0) items.push(`${plural(s.integrations, 'API key')} saved`);
		if (s && s.platforms > 0) {
			items.push(`${plural(s.platforms, 'bug bounty platform')} connected`);
		}
		if (s && s.oast_mode !== OastMode.OFF) {
			items.push(`Out-of-band testing set to ${OAST_MODE_LABELS[s.oast_mode as OastMode]}`);
		}
		if (s && s.proxies > 0) items.push(`${plural(s.proxies, 'proxy', 'proxies')} configured`);
		if (s?.ai_enabled) items.push('AI analysis enabled');
		if (s && s.channels > 0) {
			items.push(plural(s.channels, 'notification channel'));
		}
		items.push('Project created');
		return items;
	});

	let optional = $derived.by(() => {
		const status = onboardingStore.status;
		const s = status?.summary;
		if (!s) return [] as LinkItem[];
		const items: LinkItem[] = [];
		if (modeHas(status?.mode, Capability.BOUNTY_PLATFORMS) && s.platforms === 0) {
			items.push({ label: 'Bug bounty platforms', href: ROUTES.settings('api-keys') });
		}
		if (s.integrations === 0) items.push({ label: 'API keys', href: ROUTES.settings('api-keys') });
		if (s.oast_mode === OastMode.OFF) {
			items.push({ label: 'Out-of-band testing', href: ROUTES.callbackServer() });
		}
		if (s.proxies === 0) items.push({ label: 'Proxy', href: ROUTES.settings('proxies') });
		if (!s.ai_enabled) items.push({ label: 'AI analysis', href: ROUTES.settings('ai') });
		if (s.channels === 0) {
			items.push({ label: 'Notifications', href: ROUTES.settings('notifications') });
		}
		return items;
	});

	let later = $derived.by(() => {
		const items: LinkItem[] = [];
		if (modeHas(onboardingStore.status?.mode, Capability.PROGRAM_WATCHES)) {
			items.push({
				label: 'Program watches',
				detail: 'New in-scope names from certificate logs',
				href: ROUTES.bountyHubTab('watching')
			});
		}
		items.push(
			{ label: 'Remote control', detail: 'Commands from a chat app', href: ROUTES.remoteControl() },
			{ label: 'Agents', detail: 'MCP access for AI clients', href: ROUTES.agents() },
			{ label: 'Connectors', detail: 'Proxy traffic into the inventory', href: ROUTES.connectors() }
		);
		return items;
	});

	onMount(async () => {
		try {
			pending = (await datasetsApi.list()).filter(
				(d) => d.status !== FeedStatus.READY && d.status !== FeedStatus.STALE
			);
		} catch {
			pending = [];
		}
	});

	$effect(() => setFooter({ onNext: () => {}, hidden: true }));

	$effect(() => {
		(async () => {
			try {
				await onboardingApi.complete();
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Setup not completed');
			}
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
		<StepHeader icon={CircleCheckIcon} title="Setup complete" />
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

	{#if pending.length}
		<div class="mx-auto max-w-sm space-y-2.5 text-left">
			<p class="text-xs text-muted-foreground">Datasets</p>
			<ul class="space-y-2">
				{#each pending as d (d.kind)}
					<li>
						<a
							href={ROUTES.arsenal()}
							class="flex items-center justify-between gap-3 text-sm transition-colors hover:text-muted-foreground"
						>
							<span class="text-foreground">{d.label}</span>
							<span class="text-xs {FEED_STATUS_TONE[d.status]}">{d.status_label}</span>
						</a>
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	{#if optional.length}
		<div class="mx-auto max-w-sm space-y-2.5 text-left">
			<p class="text-xs text-muted-foreground">Not configured</p>
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
							<span>{item.label}</span>
							<ArrowRightIcon class="ml-auto size-3.5 opacity-60" />
						</a>
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<div class="mx-auto max-w-sm space-y-2.5 text-left">
		<p class="text-xs text-muted-foreground">Configured on their own pages</p>
		<ul class="space-y-2.5">
			{#each later as item (item.label)}
				<li>
					<a
						href={item.href}
						class="flex items-center gap-3 text-sm text-muted-foreground transition-colors hover:text-foreground"
					>
						<span class="flex min-w-0 flex-col">
							<span class="text-foreground">{item.label}</span>
							<span class="text-xs">{item.detail}</span>
						</span>
						<ArrowRightIcon class="ml-auto size-3.5 shrink-0 opacity-60" />
					</a>
				</li>
			{/each}
		</ul>
	</div>

	<div class="flex justify-center pt-2">
		<LoadingButton size="lg" onclick={launch} loading={finishing} loadingLabel="Completing setup">
			Go to dashboard
			<ArrowRightIcon class="size-4" />
		</LoadingButton>
	</div>
</div>
