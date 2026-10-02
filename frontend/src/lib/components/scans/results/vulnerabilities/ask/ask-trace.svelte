<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { TraceStatus } from '$lib/config/ask';
	import type { AskTraceStep } from '$lib/types/ask';
	import { cn } from '$lib/utils.js';
	import { inAppHref } from '$lib/utilities/mcp';

	interface Props {
		steps: AskTraceStep[];
		live?: boolean;
	}

	let { steps, live = false }: Props = $props();

	let open = $state(false);
	let rows = $derived(steps.reduce((a, s) => a + (s.rows ?? 0), 0));
	let summary = $derived(
		`${steps.length} ${steps.length === 1 ? 'lookup' : 'lookups'} · ${rows} ${rows === 1 ? 'row' : 'rows'}`
	);

	const DOT: Record<string, string> = {
		[TraceStatus.RUNNING]: 'bg-primary',
		[TraceStatus.DONE]: 'bg-success',
		[TraceStatus.FAILED]: 'bg-muted-foreground'
	};
</script>

{#snippet list()}
	<ol class="flex flex-col">
		{#each steps as step, i (i)}
			<li class="grid grid-cols-[0.875rem_minmax(0,1fr)_auto] gap-x-2.5 py-1">
				<span class="flex h-5 items-center justify-center">
					<span class={cn('size-1.5 rounded-full', DOT[step.status] ?? 'bg-muted-foreground')}
					></span>
				</span>
				<div class="flex min-w-0 flex-col">
					<span class="text-xs leading-5">
						{step.label}
						{#if step.args}
							<span class="font-mono text-2xs text-muted-foreground">{step.args}</span>
						{/if}
					</span>
					{#if step.detail}
						<span class="text-2xs leading-4 wrap-anywhere text-muted-foreground">{step.detail}</span
						>
					{/if}
				</div>
				<span class="font-mono text-2xs leading-5 text-muted-foreground tabular-nums">
					{#if step.status === TraceStatus.RUNNING}
						reading
					{:else if step.pivot && step.rows != null}
						<a href={inAppHref(step.pivot)} class="text-primary"
							>{step.rows} {step.rows === 1 ? 'row' : 'rows'}</a
						>
					{:else if step.rows != null}
						{step.rows} {step.rows === 1 ? 'row' : 'rows'}
					{:else if step.status === TraceStatus.FAILED}
						no rows
					{/if}
				</span>
			</li>
		{/each}
	</ol>
{/snippet}

{#if live}
	{@render list()}
{:else if steps.length}
	<Collapsible.Root bind:open>
		<Collapsible.Trigger
			class="flex items-center gap-1.5 text-2xs text-muted-foreground hover:text-foreground"
		>
			<ChevronDown class={cn('size-3 transition-transform', open && 'rotate-180')} />
			{summary}
		</Collapsible.Trigger>
		<Collapsible.Content class="pt-1.5">
			{@render list()}
		</Collapsible.Content>
	</Collapsible.Root>
{/if}
