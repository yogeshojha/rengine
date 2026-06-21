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

	const STEPS = [
		{ key: 'welcome-security', title: 'Welcome', component: StepWelcomeSecurity },
		{ key: 'two-factor', title: 'Two-Factor', component: StepTwoFactor },
		{ key: 'mode', title: 'Mode', component: StepMode },
		{ key: 'integrations', title: 'Integrations', component: StepIntegrations },
		{ key: 'proxy', title: 'Proxy', component: StepProxy },
		{ key: 'ai', title: 'AI', component: StepAi },
		{ key: 'notifications', title: 'Notifications', component: StepNotifications },
		{ key: 'finish', title: 'Finish', component: StepFinish },
		{ key: 'celebration', title: 'Done', component: StepCelebration }
	];

	const steps = STEPS.map((s) => ({ key: s.key, title: s.title }));

	let ready = $state(false);
	let currentIndex = $state(0);
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

{#if !ready}
	<div class="flex min-h-svh items-center justify-center gap-3 bg-background">
		<Spinner />
		<p class="text-sm text-muted-foreground">Preparing setup…</p>
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
