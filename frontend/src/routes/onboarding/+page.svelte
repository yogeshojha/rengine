<script lang="ts">
	import { goto } from '$app/navigation';
	import { untrack } from 'svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { onboardingStore } from '$lib/stores/onboarding.svelte';
	import { onboardingApi } from '$lib/api/onboarding';
	import type { StepFooter, StepProps, WizardData } from '$lib/types/onboarding';
	import { ROUTES } from '$lib/config/routes';
	import { pageTitle } from '$lib/utilities/page-title';
	import { toast } from 'svelte-sonner';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import WizardShell from '$lib/components/onboarding/wizard-shell.svelte';
	import StepWelcomeSecurity from '$lib/components/onboarding/step-welcome-security.svelte';
	import StepTwoFactor from '$lib/components/onboarding/step-two-factor.svelte';
	import StepMode from '$lib/components/onboarding/step-mode.svelte';
	import StepData from '$lib/components/onboarding/step-data.svelte';
	import StepPlatforms from '$lib/components/onboarding/step-platforms.svelte';
	import StepIntegrations from '$lib/components/onboarding/step-integrations.svelte';
	import StepOast from '$lib/components/onboarding/step-oast.svelte';
	import StepProxy from '$lib/components/onboarding/step-proxy.svelte';
	import StepAi from '$lib/components/onboarding/step-ai.svelte';
	import StepNotifications from '$lib/components/onboarding/step-notifications.svelte';
	import StepFinish from '$lib/components/onboarding/step-finish.svelte';
	import StepCelebration from '$lib/components/onboarding/step-celebration.svelte';
	import ServerCogIcon from '@lucide/svelte/icons/server-cog';
	import ServerOffIcon from '@lucide/svelte/icons/server-off';
	import EmptyState from '$lib/components/empty-state.svelte';
	import ShieldCheckIcon from '@lucide/svelte/icons/shield-check';
	import CompassIcon from '@lucide/svelte/icons/compass';
	import PlugIcon from '@lucide/svelte/icons/plug';
	import ShieldIcon from '@lucide/svelte/icons/shield';
	import BotIcon from '@lucide/svelte/icons/bot';
	import BellIcon from '@lucide/svelte/icons/bell';
	import FolderPlusIcon from '@lucide/svelte/icons/folder-plus';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import DatabaseIcon from '@lucide/svelte/icons/database';
	import SatelliteDishIcon from '@lucide/svelte/icons/satellite-dish';
	import NinjaIcon from '$lib/components/icons/ninja.svelte';
	import { Capability, modeHas, type CapabilityKey } from '$lib/config/capabilities';
	import type { IconComponent } from '$lib/config/icons';
	import type { Component } from 'svelte';

	interface Step {
		title: string;
		description: string;
		icon: IconComponent;
		component: Component<StepProps>;
		capability?: CapabilityKey;
	}

	const ALL_STEPS: Step[] = [
		{
			title: 'Instance setup',
			description: 'Instance name, time zone and administrator password.',
			icon: ServerCogIcon,
			component: StepWelcomeSecurity
		},
		{
			title: 'Two-factor authentication',
			description: 'Second factor for the administrator account, from an authenticator app.',
			icon: ShieldCheckIcon,
			component: StepTwoFactor
		},
		{
			title: 'Operating mode',
			description: 'One mode is active at a time. Corporate hides bug bounty tooling.',
			icon: CompassIcon,
			component: StepMode
		},
		{
			title: 'Data',
			description: 'Worker status, downloaded datasets and retention.',
			icon: DatabaseIcon,
			component: StepData
		},
		{
			title: 'Bug bounty platforms',
			description: 'Platform API tokens add private programs and their scope.',
			icon: NinjaIcon,
			component: StepPlatforms,
			capability: Capability.BOUNTY_PLATFORMS
		},
		{
			title: 'API keys',
			description: 'Keys for subdomain sources, lookups and exploit intelligence.',
			icon: PlugIcon,
			component: StepIntegrations
		},
		{
			title: 'Out-of-band testing',
			description: 'Callback server for checks that confirm a finding out of band.',
			icon: SatelliteDishIcon,
			component: StepOast
		},
		{
			title: 'Proxy',
			description: 'Optional. Scan traffic exits through the proxy.',
			icon: ShieldIcon,
			component: StepProxy
		},
		{
			title: 'AI analysis',
			description:
				'A language model summarizes findings and drafts remediation. A computed summary of each scan is sent to the selected provider.',
			icon: BotIcon,
			component: StepAi
		},
		{
			title: 'Notifications',
			description: 'Scan events sent to Slack, Discord, Telegram or a webhook.',
			icon: BellIcon,
			component: StepNotifications
		},
		{
			title: 'Create a project',
			description: 'First project on this instance.',
			icon: FolderPlusIcon,
			component: StepFinish
		},
		{
			title: 'Setup complete',
			description: 'This instance is configured.',
			icon: CircleCheckIcon,
			component: StepCelebration
		}
	];

	let ready = $state(false);
	let loadFailed = $state(false);
	let currentIndex = $state(0);
	let data = $state<WizardData>({ mode: null, instanceName: '', twoFactorEnabled: false });

	const STEPS = $derived(
		ALL_STEPS.filter((step) => !step.capability || modeHas(data.mode, step.capability))
	);
	const steps = $derived(
		STEPS.map((s) => ({
			title: s.title,
			description: s.description,
			icon: s.icon
		}))
	);

	let fcfg = $state<StepFooter>({ onNext: () => {} });
	function setFooter(cfg: StepFooter) {
		fcfg = {
			onNext: cfg.onNext,
			nextLabel: cfg.nextLabel ?? 'Continue',
			nextLoading: cfg.nextLoading ?? false,
			nextLoadingLabel: cfg.nextLoadingLabel,
			nextDisabled: cfg.nextDisabled ?? false,
			canSkip: cfg.canSkip ?? false,
			hidden: cfg.hidden ?? false
		};
	}

	$effect(() => {
		if (auth.isLoading) return;
		if (!auth.isAuthenticated) {
			if (!auth.unreachable) goto(ROUTES.login);
			return;
		}
		untrack(guard);
	});

	async function guard() {
		loadFailed = false;
		await onboardingStore.refresh();
		const status = onboardingStore.status;
		if (!status) {
			loadFailed = true;
			return;
		}
		if (status.completed || !status.can_setup) {
			goto(ROUTES.dashboard);
			return;
		}
		data.instanceName = status.instance_name ?? '';
		data.mode = status.mode ?? null;
		const lastStep = STEPS.length - 2;
		const resumeAt = Math.max(0, Math.min(status.current_step ?? 0, lastStep));
		if (resumeAt > 0) {
			currentIndex = resumeAt;
			toast.info('Saved progress restored');
		}
		ready = true;
	}

	function persistProgress(step: number) {
		onboardingApi.saveProgress(step, { mode: data.mode }).catch(() => {});
	}

	function next() {
		if (currentIndex < STEPS.length - 1) {
			currentIndex += 1;
			persistProgress(currentIndex);
		}
	}

	function back() {
		if (currentIndex > 0) {
			currentIndex -= 1;
			persistProgress(currentIndex);
		}
	}

	function skip() {
		next();
	}
</script>

<svelte:head><title>{pageTitle(STEPS[currentIndex]?.title ?? 'Setup')}</title></svelte:head>

{#if auth.unreachable}
	<div class="flex min-h-svh items-center justify-center bg-background p-6">
		<EmptyState
			icon={ServerOffIcon}
			title="Server not reachable"
			description={auth.unreachable}
			class="w-full max-w-lg"
		>
			<Button size="sm" variant="outline" onclick={() => auth.checkAuth([])}>Retry</Button>
		</EmptyState>
	</div>
{:else if loadFailed}
	<div class="flex min-h-svh flex-col items-center justify-center gap-3 bg-background">
		<p class="text-sm text-muted-foreground">
			The API did not respond. Check that the api service is running.
		</p>
		<Button variant="outline" size="sm" onclick={() => guard()}>Retry</Button>
	</div>
{:else if !ready}
	<div class="flex min-h-svh items-center justify-center gap-3 bg-background">
		<Spinner />
		<p class="text-sm text-muted-foreground">Loading setup</p>
	</div>
{:else}
	<WizardShell
		{steps}
		{currentIndex}
		footer={fcfg}
		onBack={back}
		onSkip={skip}
		isFirst={currentIndex === 0}
	>
		{@const Step = STEPS[currentIndex].component}
		<Step {data} {next} {setFooter} />
	</WizardShell>
{/if}
