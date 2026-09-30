<script lang="ts">
	import { Separator } from '$lib/components/ui/separator';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import { FactTone } from '$lib/config/ask';
	import type { AskBrief, AskFact } from '$lib/types/ask';
	import { cn } from '$lib/utils.js';

	interface Props {
		brief: AskBrief | null;
		loading?: boolean;
		onFact?: (fact: AskFact) => void;
	}

	let { brief, loading = false, onFact }: Props = $props();

	const MARK: Record<string, string> = {
		[FactTone.FOR]: 'bg-primary text-primary-foreground',
		[FactTone.AGAINST]: 'bg-warning text-warning-foreground',
		[FactTone.UNKNOWN]: 'bg-muted text-muted-foreground'
	};
</script>

<div class="flex items-center gap-3 border-b bg-muted/30 px-5 py-2.5">
	<div class="flex shrink-0 flex-col">
		<span class="text-2xs tracking-wide text-muted-foreground uppercase">Verdict</span>
		{#if loading || !brief}
			<Skeleton class="mt-1 h-4 w-20" />
		{:else}
			<span class="text-sm font-semibold">{brief.label}</span>
		{/if}
	</div>
	<Separator orientation="vertical" class="h-6" />
	<div class="flex min-w-0 flex-wrap gap-1.5">
		{#if loading || !brief}
			<Skeleton class="h-6 w-28" />
			<Skeleton class="h-6 w-24" />
		{:else if !brief.facts.length}
			<span class="text-xs text-muted-foreground">No stored facts bear on it.</span>
		{:else}
			{#each brief.facts as fact (fact.n)}
				<Hint text={fact.detail}>
					{#snippet child(props)}
						<button
							{...props}
							type="button"
							disabled={!fact.lines.length || !onFact}
							onclick={() => onFact?.(fact)}
							class={cn(
								'inline-flex h-6 items-center gap-1.5 rounded-md border bg-card px-2 text-xs whitespace-nowrap',
								fact.tone === FactTone.UNKNOWN && 'border-dashed text-muted-foreground',
								fact.lines.length && onFact ? 'cursor-pointer hover:bg-accent' : 'cursor-default'
							)}
						>
							<span
								class={cn(
									'inline-flex size-3.5 items-center justify-center rounded-sm font-mono text-2xs font-semibold',
									MARK[fact.tone]
								)}>{fact.n}</span
							>
							{fact.label}
						</button>
					{/snippet}
				</Hint>
			{/each}
		{/if}
	</div>
</div>
