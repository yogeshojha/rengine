<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { onboardingStore } from '$lib/stores/onboarding.svelte';
	import { onboardingApi } from '$lib/api/onboarding';
	import type { StepFooter, WizardData } from '$lib/types/onboarding';
	import { ROUTES } from '$lib/config/routes';
	import { toast } from 'svelte-sonner';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import WizardShell from '$lib/components/onboarding/wizard-shell.svelte';
	import StepWelcomeSecurity from '$lib/components/onboarding/step-welcome-security.svelte';
	import StepTwoFactor from '$lib/components/onboarding/step-two-factor.svelte';
	import StepMode from '$lib/components/onboarding/step-mode.svelte';
	import StepIntegrations from '$lib/components/onboarding/step-integrations.svelte';
	import StepProxy from '$lib/components/onboarding/step-proxy.svelte';
	import StepAi from '$lib/components/onboarding/step-ai.svelte';
	import StepNotifications from '$lib/components/onboarding/step-notifications.svelte';
	import StepFinish from '$lib/components/onboarding/step-finish.svelte';
	import StepCelebration from '$lib/components/onboarding/step-celebration.svelte';
	import ServerCogIcon from '@lucide/svelte/icons/server-cog';
	import ShieldCheckIcon from '@lucide/svelte/icons/shield-check';
	import CompassIcon from '@lucide/svelte/icons/compass';
	import PlugIcon from '@lucide/svelte/icons/plug';
	import ShieldIcon from '@lucide/svelte/icons/shield';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import BellIcon from '@lucide/svelte/icons/bell';
	import FolderPlusIcon from '@lucide/svelte/icons/folder-plus';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';

	const STEPS = [
		{
			key: 'welcome-security',
			title: 'Welcome to reNgine',
			description: 'Configure this instance. Every setting here can be changed later in Settings.',
			icon: ServerCogIcon,
			component: StepWelcomeSecurity
		},
		{
			key: 'two-factor',
			title: 'Secure this account',
			description:
				'Add a second factor with an authenticator app. This can also be set up later from the profile page.',
			icon: ShieldCheckIcon,
			component: StepTwoFactor
		},
		{
			key: 'mode',
			title: 'Operating mode',
			description:
				'One mode is active at a time. Corporate hides bug bounty tooling; bug bounty adds the HackerOne integration. The mode can be changed in Settings.',
			icon: CompassIcon,
			component: StepMode
		},
		{
			key: 'integrations',
			title: 'Connect data sources',
			description:
				'Optional API keys that expand passive recon. These can also be added in Settings, under API keys.',
			icon: PlugIcon,
			component: StepIntegrations
		},
		{
			key: 'proxy',
			title: 'Route scans through a proxy',
			description:
				'Keeps the source IP off WAF blocklists and distributes load across exit addresses. Optional, and recommended for sustained scanning.',
			icon: ShieldIcon,
			component: StepProxy
		},
		{
			key: 'ai',
			title: 'AI analysis',
			description:
				'Use a language model to summarize findings and draft remediation. Scan data is sent to the provider you choose.',
			icon: SparklesIcon,
			component: StepAi
		},
		{
			key: 'notifications',
			title: 'Connect notifications',
			description:
				'Route scan and recon events to Slack, Discord, Telegram or a webhook. Email, Teams and other destinations can be added in Settings.',
			icon: BellIcon,
			component: StepNotifications
		},
		{
			key: 'finish',
			title: 'Create your first project',
			description:
				'A project keeps targets, scans and findings separate. Set data retention and name the first one.',
			icon: FolderPlusIcon,
			component: StepFinish
		},
		{
			key: 'celebration',
			title: 'Setup complete',
			description: 'This instance is configured.',
			icon: CircleCheckIcon,
			component: StepCelebration
		}
	];

	const steps = STEPS.map((s) => ({
		key: s.key,
		title: s.title,
		description: s.description,
		icon: s.icon
	}));

	let ready = $state(false);
	let currentIndex = $state(0);
	let direction = $state<'forward' | 'back'>('forward');
	let data = $state<WizardData>({ mode: null, instanceName: '', twoFactorEnabled: false });

	let fcfg = $state<StepFooter>({ onNext: () => {} });
	function setFooter(cfg: StepFooter) {
		fcfg = {
			onNext: cfg.onNext,
			nextLabel: cfg.nextLabel ?? 'Continue',
			nextLoading: cfg.nextLoading ?? false,
			nextDisabled: cfg.nextDisabled ?? false,
			canSkip: cfg.canSkip ?? false,
			hidden: cfg.hidden ?? false
		};
	}

	$effect(() => {
		if (auth.isLoading) return;
		if (!auth.isAuthenticated) {
			goto(ROUTES.login);
			return;
		}
		guard();
	});

	async function guard() {
		await onboardingStore.fetchStatus();
		const status = onboardingStore.status;
		if (!status) return;
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
			toast.info('Restoring your progress');
		}
		ready = true;
	}

	function persistProgress(step: number) {
		onboardingApi.saveProgress(step, { mode: data.mode }).catch(() => {});
	}

	function next() {
		if (currentIndex < STEPS.length - 1) {
			direction = 'forward';
			currentIndex += 1;
			persistProgress(currentIndex);
		}
	}

	function back() {
		if (currentIndex > 0) {
			direction = 'back';
			currentIndex -= 1;
			persistProgress(currentIndex);
		}
	}

	function skip() {
		next();
	}
</script>

{#if !ready}
	<div class="flex min-h-svh items-center justify-center gap-3 bg-background">
		<Spinner />
		<p class="text-sm text-muted-foreground">Preparing setup…</p>
	</div>
{:else}
	<WizardShell
		{steps}
		{currentIndex}
		{direction}
		footer={fcfg}
		onBack={back}
		onSkip={skip}
		isFirst={currentIndex === 0}
	>
		{@const Step = STEPS[currentIndex].component}
		<Step
			{data}
			{next}
			{back}
			{skip}
			{setFooter}
			isFirst={currentIndex === 0}
			isLast={currentIndex === STEPS.length - 1}
		/>
	</WizardShell>
{/if}
