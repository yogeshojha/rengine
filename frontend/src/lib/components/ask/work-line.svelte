<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Copy from '@lucide/svelte/icons/copy';
	import X from '@lucide/svelte/icons/x';
	import { Spinner } from '$lib/components/ui/spinner';
	import Hint from '$lib/components/hint.svelte';
	import { TraceStatus } from '$lib/config/ask';
	import { cn } from '$lib/utils.js';
	import type { AskTraceStep } from '$lib/types/ask';

	export interface FunnelStep {
		count: number;
		capped?: boolean;
		label: string;
	}

	interface Props {
		steps: AskTraceStep[];
		live: boolean;
		funnel: FunnelStep[];
		onCopy?: () => void;
	}

	let { steps, live, funnel, onCopy }: Props = $props();

	let open = $state(false);
	let seconds = $derived(steps.reduce((sum, s) => sum + (s.ms ?? 0), 0) / 1000);
	let calls = $derived(steps.length);
	let lookups = $derived(`${calls} ${calls === 1 ? 'lookup' : 'lookups'}`);
</script>

{#snippet list()}
	<ol class="flex flex-col gap-1.5">
		{#each steps as step, i (i)}
			<li
				class={cn(
					'grid grid-cols-[1.125rem_minmax(0,1fr)_auto] items-center gap-2.5 text-sm',
					step.status === TraceStatus.FAILED && 'text-muted-foreground'
				)}
			>
				<span class="flex size-4.5 items-center justify-center rounded-full bg-muted">
					{#if step.status === TraceStatus.RUNNING}
						<Spinner class="size-3 text-primary" />
					{:else if step.status === TraceStatus.DONE}
						<Check class="size-3 text-success" />
					{:else}
						<X class="size-3" />
					{/if}
				</span>
				<span class={['min-w-0 truncate', step.status === TraceStatus.RUNNING && 'ask-shimmer']}>
					{step.label}
					{#if step.status === TraceStatus.FAILED && step.detail}
						<span class="text-xs">· {step.detail}</span>
					{/if}
				</span>
				<span class="text-xs text-muted-foreground tabular-nums"
					>{step.rows != null ? step.rows.toLocaleString() : ''}</span
				>
			</li>
		{/each}
	</ol>
{/snippet}

{#if live}
	{#if steps.length}
		{@render list()}
	{/if}
{:else if steps.length || funnel.length}
	<div class="flex flex-col gap-2">
		<div
			class="flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-muted-foreground"
		>
			<span class="flex size-4.5 shrink-0 items-center justify-center rounded-full bg-muted">
				<Check class="size-3 text-success" />
			</span>
			{#each funnel as f, i (i)}
				{#if i > 0}<span aria-hidden="true">›</span>{/if}
				<span
					><b class="font-semibold text-foreground tabular-nums"
						>{f.count.toLocaleString()}{f.capped ? '+' : ''}</b
					>
					{f.label}</span
				>
			{/each}
			<span class="ml-auto flex items-center gap-1">
				{#if steps.length}
					<button
						type="button"
						class="inline-flex h-6 items-center gap-1 rounded-md px-1.5 hover:bg-muted hover:text-foreground"
						aria-expanded={open}
						onclick={() => (open = !open)}
					>
						{lookups} · {seconds.toFixed(1)} s
						<ChevronDown class={cn('size-3', open && 'rotate-180')} />
					</button>
				{/if}
				{#if onCopy}
					<Hint text="Copy answer">
						{#snippet child(props)}
							<button
								{...props}
								type="button"
								class="inline-flex size-6 items-center justify-center rounded-md hover:bg-muted hover:text-foreground"
								onclick={onCopy}
								aria-label="Copy answer"
							>
								<Copy class="size-3.5" />
							</button>
						{/snippet}
					</Hint>
				{/if}
			</span>
		</div>
		{#if open}
			<div class="rounded-lg border bg-card px-3 py-2.5">{@render list()}</div>
		{/if}
	</div>
{/if}
