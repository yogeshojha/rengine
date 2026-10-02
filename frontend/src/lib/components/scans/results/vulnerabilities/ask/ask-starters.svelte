<script lang="ts">
	import { untrack } from 'svelte';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { askBriefs, briefKey } from '$lib/api/ask';
	import { MAX_STARTERS } from '$lib/config/ask';
	import type { AskBrief, AskSubject } from '$lib/types/ask';
	import { cn } from '$lib/utils.js';

	interface Props {
		subject: AskSubject;
		onAsk: (question: string) => void;
		class?: string;
	}

	let { subject, onAsk, class: className }: Props = $props();

	let brief = $state<AskBrief | null>(null);
	let loading = $state(false);
	let generation = 0;

	let key = $derived(briefKey(subject));
	let starters = $derived(
		brief?.available ? [...new Set(brief.starters)].slice(0, MAX_STARTERS) : []
	);

	$effect(() => {
		void key;
		untrack(load);
	});

	function load() {
		const mine = ++generation;
		const held = askBriefs.peek(subject);
		brief = held;
		loading = !held && askBriefs.lastAvailable !== false;
		if (held) return;
		askBriefs.get(subject).then(
			(b) => {
				if (mine !== generation) return;
				brief = b;
				loading = false;
			},
			() => {
				if (mine === generation) loading = false;
			}
		);
	}
</script>

{#if loading}
	<Skeleton class={cn('h-7 w-80 max-w-full rounded-full', className)} />
{:else if starters.length}
	<div class={cn('flex flex-wrap items-center gap-1.5', className)}>
		<Sparkles class="size-3.5 shrink-0 text-primary" aria-hidden="true" />
		{#each starters as starter (starter)}
			<Button
				variant="outline"
				size="sm"
				class="h-7 rounded-full px-3 text-xs font-normal"
				onclick={() => onAsk(starter)}>{starter}</Button
			>
		{/each}
	</div>
{/if}
