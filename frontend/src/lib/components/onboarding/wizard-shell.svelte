<script lang="ts">
	import type { Snippet } from 'svelte';
	import { fly } from 'svelte/transition';
	import { cubicIn, cubicOut } from 'svelte/easing';
	import BoxesIcon from '@lucide/svelte/icons/boxes';
	import { Progress } from '$lib/components/ui/progress/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { PrefersReducedMotion } from '$lib/hooks/prefers-reduced-motion.svelte';
	import WizardFooter from './wizard-footer.svelte';
	import type { StepFooter } from '$lib/types/onboarding';

	interface Props {
		steps: { key: string; title: string }[];
		currentIndex: number;
		direction: 'forward' | 'back';
		footer: StepFooter;
		onBack: () => void;
		onSkip: () => void;
		isFirst: boolean;
		children: Snippet;
	}

	let { steps, currentIndex, direction, footer, onBack, onSkip, isFirst, children }: Props = $props();

	let total = $derived(steps.length);
	let current = $derived(steps[currentIndex]);
	let pct = $derived(total > 0 ? Math.round(((currentIndex + 1) / total) * 100) : 0);

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

<div class="flex h-dvh flex-col bg-background">
	<Progress
		value={pct}
		class="h-0.5 w-full shrink-0 rounded-none transition-all duration-500 ease-out"
	/>

	<header class="shrink-0 border-b">
		<div class="mx-auto flex w-full max-w-xl items-center justify-between gap-3 px-6 py-4 sm:px-8">
			<div class="flex items-center gap-2">
				<div
					class="bg-primary text-primary-foreground flex size-6 items-center justify-center rounded-md"
				>
					<BoxesIcon class="size-3.5" />
				</div>
				<span class="text-sm font-semibold tracking-tight">reNgine setup</span>
			</div>
			<span class="text-xs font-medium tabular-nums text-muted-foreground">
				Step {currentIndex + 1} of {total}
			</span>
		</div>
	</header>

	<main class="min-h-0 flex-1" aria-label="Setup">
		<ScrollArea class="h-full">
			<div
				bind:this={bodyEl}
				tabindex="-1"
				class="mx-auto flex min-h-full w-full max-w-xl flex-col justify-center px-6 py-12 outline-none sm:px-8 sm:py-16"
			>
				<div class="grid">
					{#key currentIndex}
						<div class="[grid-area:1/1]" in:fly={transIn} out:fly={transOut}>
							{@render children()}
						</div>
					{/key}
				</div>
			</div>
		</ScrollArea>
	</main>

	{#if !footer.hidden}
		<footer class="shrink-0 border-t">
			<div class="mx-auto w-full max-w-xl px-6 py-4 sm:px-8">
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

	<div class="sr-only" role="status" aria-live="polite">
		Step {currentIndex + 1} of {total}, {current?.title}
	</div>
</div>
