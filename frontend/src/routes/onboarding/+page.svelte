<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { onboardingStore } from '$lib/stores/onboarding.svelte';
	import { onboardingApi } from '$lib/api/onboarding';
	import type { StepFooter, WizardData } from '$lib/types/onboarding';
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
	import RocketIcon from '@lucide/svelte/icons/rocket';
	import ShieldCheckIcon from '@lucide/svelte/icons/shield-check';
	import CompassIcon from '@lucide/svelte/icons/compass';
	import PlugIcon from '@lucide/svelte/icons/plug';
	import ShieldIcon from '@lucide/svelte/icons/shield';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import BellIcon from '@lucide/svelte/icons/bell';
	import FolderPlusIcon from '@lucide/svelte/icons/folder-plus';
	import PartyPopperIcon from '@lucide/svelte/icons/party-popper';

	const STEPS = [
		{
			key: 'welcome-security',
			title: 'Welcome to reNgine',
			description:
				"Let's get your instance set up. It takes a couple of minutes, and you can change everything later in Settings.",
			icon: RocketIcon,
			component: StepWelcomeSecurity
		},
		{
			key: 'two-factor',
			title: 'Secure your account',
			description:
				'Add a second factor with an authenticator app. You can also set this up later from your profile.',
			icon: ShieldCheckIcon,
			component: StepTwoFactor
		},
		{
			key: 'mode',
			title: 'How will you use reNgine?',
			description:
				'Pick one — it tailors which features appear. Corporate hides bug-bounty tooling entirely. You can switch anytime in Settings.',
			icon: CompassIcon,
			component: StepMode
		},
		{
			key: 'integrations',
			title: 'Connect data sources',
			description:
				'Optional API keys that expand passive recon. Add any now, or later in Settings → API Keys.',
			icon: PlugIcon,
			component: StepIntegrations
		},
		{
			key: 'proxy',
			title: 'Route scans through a proxy',
			description:
				'Keep your source IP off WAF blocklists and distribute load across exit IPs. Optional, but recommended beyond light use.',
			icon: ShieldIcon,
			component: StepProxy
		},
		{
			key: 'ai',
			title: 'AI-powered analysis',
			description:
				'Use an LLM to summarize findings and draft remediation. Scan data is sent to the provider you choose.',
			icon: SparklesIcon,
			component: StepAi
		},
		{
			key: 'notifications',
			title: 'Connect notifications',
			description:
				'Route scan and recon events to Slack, Discord, Telegram, or a generic webhook. Add email, Teams, and more later in Settings.',
			icon: BellIcon,
			component: StepNotifications
		},
		{
			key: 'finish',
			title: 'Create your first project',
			description:
				'Projects organize targets, scans, and findings. Set data retention and name your first one.',
			icon: FolderPlusIcon,
			component: StepFinish
		},
		{
			key: 'celebration',
			title: "You're all set",
			description: 'reNgine is configured and ready.',
			icon: PartyPopperIcon,
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
			goto('/login');
			return;
		}
		guard();
	});

	async function guard() {
		await onboardingStore.fetchStatus();
		const status = onboardingStore.status;
		if (!status) return;
		if (status.completed || !status.can_setup) {
			goto('/dashboard');
			return;
		}
		data.instanceName = status.instance_name ?? '';
		data.mode = status.mode ?? null;
		const lastStep = STEPS.length - 2;
		const resumeAt = Math.max(0, Math.min(status.current_step ?? 0, lastStep));
		if (resumeAt > 0) {
			currentIndex = resumeAt;
			toast.info('Resuming where you left off');
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
