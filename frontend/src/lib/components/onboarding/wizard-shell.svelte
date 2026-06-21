<script lang="ts">
	import type { Snippet } from 'svelte';
	import { fade } from 'svelte/transition';
	import { cubicIn, cubicOut } from 'svelte/easing';
	import BoxesIcon from '@lucide/svelte/icons/boxes';
	import CheckIcon from '@lucide/svelte/icons/check';
	import { cn } from '$lib/utils.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Progress } from '$lib/components/ui/progress/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import WizardFooter from './wizard-footer.svelte';
	import type { StepFooter } from '$lib/types/onboarding';

	interface Props {
		steps: { key: string; title: string }[];
		currentIndex: number;
		footer: StepFooter;
		onBack: () => void;
		onSkip: () => void;
		isFirst: boolean;
		children: Snippet;
	}

	let { steps, currentIndex, footer, onBack, onSkip, isFirst, children }: Props = $props();

	let total = $derived(steps.length);
	let current = $derived(steps[currentIndex]);
	let pct = $derived(total > 0 ? Math.round(((currentIndex + 1) / total) * 100) : 0);

	function stateOf(i: number): 'done' | 'current' | 'upcoming' {
		if (i < currentIndex) return 'done';
		if (i === currentIndex) return 'current';
		return 'upcoming';
	}
</script>

<Dialog.Root open={true}>
	<Dialog.Content
		showCloseButton={false}
		interactOutsideBehavior="ignore"
		escapeKeydownBehavior="ignore"
		class="top-[7vh] grid max-h-[86vh] translate-y-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-0 overflow-hidden p-0 sm:max-w-2xl"
	>
		<Dialog.Title class="sr-only">Set up reNgine — {current?.title}</Dialog.Title>

		<div class="border-b px-6 py-5">
			<div class="flex items-center justify-between gap-3">
				<div class="flex items-center gap-2">
					<div class="bg-primary text-primary-foreground flex size-6 items-center justify-center rounded-md">
						<BoxesIcon class="size-3.5" />
					</div>
					<span class="text-sm font-semibold tracking-tight">reNgine setup</span>
				</div>
				<span class="text-xs font-medium text-muted-foreground">
					Step {currentIndex + 1} of {total} · {current?.title}
				</span>
			</div>
			<Progress value={pct} class="mt-4 h-1 transition-all duration-300 ease-out" />
		</div>

		<div class="flex min-h-0">
			<nav aria-label="Setup steps" class="bg-muted/30 hidden w-48 shrink-0 border-r px-3 py-6 sm:block">
				<ol class="space-y-0.5">
					{#each steps as step, i (step.key)}
						{@const st = stateOf(i)}
						<li
							class={cn(
								'flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-xs transition-colors',
								st === 'current' && 'bg-background text-foreground font-medium shadow-sm',
								st === 'done' && 'text-muted-foreground',
								st === 'upcoming' && 'text-muted-foreground/60'
							)}
							aria-current={st === 'current' ? 'step' : undefined}
						>
							<span
								class={cn(
									'flex size-4 shrink-0 items-center justify-center rounded-full border text-[10px] font-medium',
									st === 'current' && 'border-primary bg-primary text-primary-foreground',
									st === 'done' && 'border-foreground/30 bg-foreground/10 text-foreground',
									st === 'upcoming' && 'border-muted-foreground/30'
								)}
							>
								{#if st === 'done'}
									<CheckIcon class="size-3" />
								{:else}
									{i + 1}
								{/if}
							</span>
							<span class="truncate">{step.title}</span>
						</li>
					{/each}
				</ol>
			</nav>

			<ScrollArea class="min-h-0 flex-1">
				<div class="px-6 py-6">
					<div class="grid min-h-[21rem]">
						{#key currentIndex}
							<div
								class="[grid-area:1/1]"
								in:fade={{ duration: 150, easing: cubicOut }}
								out:fade={{ duration: 120, easing: cubicIn }}
							>
								{@render children()}
							</div>
						{/key}
					</div>
				</div>
			</ScrollArea>
		</div>

		{#if !footer.hidden}
			<div class="border-t px-6 py-4">
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
		{/if}
	</Dialog.Content>
</Dialog.Root>
