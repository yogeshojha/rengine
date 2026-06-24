<script lang="ts">
	import type { Snippet, Component } from 'svelte';
	import { fly } from 'svelte/transition';
	import { cubicIn, cubicOut } from 'svelte/easing';
	import BoxesIcon from '@lucide/svelte/icons/boxes';
	import { Progress } from '$lib/components/ui/progress/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { PrefersReducedMotion } from '$lib/hooks/prefers-reduced-motion.svelte';
	import WizardFooter from './wizard-footer.svelte';
	import type { StepFooter } from '$lib/types/onboarding';

	interface StepMeta {
		key: string;
		title: string;
		description: string;
		icon: Component;
	}

	interface Props {
		steps: StepMeta[];
		currentIndex: number;
		direction: 'forward' | 'back';
		footer: StepFooter;
		onBack: () => void;
		onSkip: () => void;
		isFirst: boolean;
		children: Snippet;
	}

	let { steps, currentIndex, direction, footer, onBack, onSkip, isFirst, children }: Props =
		$props();

	let total = $derived(steps.length);
	let current = $derived(steps[currentIndex]);
	let pct = $derived(total > 0 ? Math.round(((currentIndex + 1) / total) * 100) : 0);
	let isCelebration = $derived(currentIndex === total - 1);

	const reduce = new PrefersReducedMotion();
	let dx = $derived(direction === 'back' ? -8 : 8);
	let transIn = $derived(
		reduce.current
			? { x: 0, duration: 90, easing: cubicOut }
			: { x: dx, duration: 260, easing: cubicOut }
	);
	let transOut = $derived(
		reduce.current
			? { x: 0, duration: 70, easing: cubicIn }
			: { x: -dx, duration: 170, easing: cubicIn }
	);

	let bodyEl = $state<HTMLElement | null>(null);
	$effect(() => {
		const _step = currentIndex;
		bodyEl?.focus({ preventScroll: true });
	});
</script>

{#snippet brand()}
	<div class="flex items-center gap-2">
		<div
			class="bg-primary text-primary-foreground flex size-6 items-center justify-center rounded-md"
		>
			<BoxesIcon class="size-3.5" />
		</div>
		<span class="text-sm font-semibold tracking-tight">reNgine setup</span>
	</div>
{/snippet}

{#snippet stepBody()}
	<div class="grid">
		{#key currentIndex}
			<div class="[grid-area:1/1]" in:fly={transIn} out:fly={transOut}>
				{@render children()}
			</div>
		{/key}
	</div>
{/snippet}

<div class="sr-only" role="status" aria-live="polite">
	Step {currentIndex + 1} of {total}, {current?.title}
</div>

{#if isCelebration}
	<div class="flex h-dvh flex-col bg-background">
		<Progress value={pct} class="h-0.5 w-full shrink-0 rounded-none" />
		<main class="min-h-0 flex-1">
			<ScrollArea class="h-full">
				<div
					bind:this={bodyEl}
					tabindex="-1"
					class="mx-auto flex min-h-full w-full max-w-xl flex-col justify-center px-6 py-12 outline-none"
				>
					{@render stepBody()}
				</div>
			</ScrollArea>
		</main>
	</div>
{:else}
	{@const Icon = current?.icon}
	<div class="flex h-dvh bg-background">
		<aside
			class="hidden w-[38%] max-w-lg shrink-0 flex-col justify-between border-r bg-muted/30 p-10 lg:flex xl:p-14"
		>
			{@render brand()}

			<div class="flex flex-col gap-5 py-10">
				{#if Icon}
					<div
						class="flex size-12 items-center justify-center rounded-xl border bg-background text-foreground shadow-sm"
					>
						<Icon class="size-6" />
					</div>
				{/if}
				<div class="space-y-3">
					<h1 class="text-3xl font-semibold leading-tight tracking-tight text-foreground">
						{current?.title}
					</h1>
					<p class="text-base leading-relaxed text-muted-foreground">{current?.description}</p>
				</div>
			</div>

			<div class="space-y-2.5">
				<div class="flex items-center justify-between text-xs font-medium text-muted-foreground">
					<span>Step {currentIndex + 1} of {total}</span>
					<span class="tabular-nums">{pct}%</span>
				</div>
				<Progress value={pct} class="h-1 transition-all duration-500 ease-out" />
			</div>
		</aside>

		<div class="flex min-w-0 flex-1 flex-col">
			<header class="shrink-0 border-b lg:hidden">
				<div class="flex items-center justify-between px-6 py-3">
					{@render brand()}
					<span class="text-xs font-medium tabular-nums text-muted-foreground">
						{currentIndex + 1} / {total}
					</span>
				</div>
				<Progress value={pct} class="h-0.5 w-full rounded-none" />
				<div class="space-y-1 px-6 pb-4 pt-3">
					<h1 class="text-lg font-semibold tracking-tight">{current?.title}</h1>
					<p class="text-sm text-muted-foreground">{current?.description}</p>
				</div>
			</header>

			<main class="min-h-0 flex-1" aria-label="Setup">
				<ScrollArea class="h-full">
					<div
						bind:this={bodyEl}
						tabindex="-1"
						class="mx-auto flex min-h-full w-full max-w-2xl flex-col justify-center px-6 py-10 outline-none sm:px-10 lg:py-14"
					>
						{@render stepBody()}
					</div>
				</ScrollArea>
			</main>

			{#if !footer.hidden}
				<footer class="shrink-0 border-t">
					<div class="mx-auto w-full max-w-2xl px-6 py-4 sm:px-10">
						<WizardFooter
							{onBack}
							{onSkip}
							{isFirst}
							onNext={footer.onNext}
							nextLabel={footer.nextLabel ?? 'Continue'}
							nextLoading={footer.nextLoading ?? false}
							nextDisabled={footer.nextDisabled ?? false}
							canSkip={footer.canSkip ?? false}
						/>
					</div>
				</footer>
			{/if}
		</div>
	</div>
{/if}
