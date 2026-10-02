<script lang="ts">
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import Radar from '@lucide/svelte/icons/radar';
	import Filter from '@lucide/svelte/icons/filter';
	import Bell from '@lucide/svelte/icons/bell';
	import type { IconComponent } from '$lib/config/icons';
	import {
		FIRE_ON_CLAUSE,
		dimensionSpec,
		fireOnLabel,
		triggerLabel,
		type FireOn
	} from '$lib/config/tripwires';
	import QueryChip from './query-chip.svelte';

	export type FlowNode = 'when' | 'if' | 'then';

	export interface FlowAction {
		label: string;
		detail: string;
	}

	interface Props {
		current: FlowNode | null;
		trigger: string;
		scopeText: string;
		dimension: string;
		query: string;
		fireOn: string;
		actions: FlowAction[];
	}

	let { current, trigger, scopeText, dimension, query, fireOn, actions }: Props = $props();

	let spec = $derived(dimensionSpec(dimension));

	interface Node {
		key: FlowNode;
		title: string;
		icon: IconComponent;
	}

	const NODES: Node[] = [
		{ key: 'when', title: 'When', icon: Radar },
		{ key: 'if', title: 'If', icon: Filter },
		{ key: 'then', title: 'Then', icon: Bell }
	];

	function tone(key: FlowNode): string {
		if (current === key) return 'border-primary/60 bg-primary/5';
		return 'border-border bg-muted/20';
	}
</script>

<ol
	class="flex flex-col gap-1 sm:flex-row sm:items-stretch sm:gap-2"
	aria-label="What this tripwire does"
>
	{#each NODES as node, index (node.key)}
		{@const Icon = node.icon}
		<li class="flex min-w-0 flex-1 flex-col gap-1 sm:flex-row sm:items-stretch sm:gap-2">
			<div
				class="flex min-w-0 flex-1 gap-3 rounded-lg border px-3 py-2.5 transition-colors {tone(
					node.key
				)}"
				aria-current={current === node.key ? 'step' : undefined}
			>
				<span
					class="flex size-7 shrink-0 items-center justify-center rounded-md {current === node.key
						? 'bg-primary text-primary-foreground'
						: 'bg-muted text-muted-foreground'}"
				>
					<Icon class="size-4" />
				</span>
				<span class="flex min-w-0 flex-col gap-0.5">
					<span class="text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase">
						{node.title}
					</span>
					{#if node.key === 'when'}
						<span class="text-sm">{triggerLabel(trigger)}</span>
						<span class="truncate text-xs text-muted-foreground">{scopeText}</span>
					{:else if node.key === 'if'}
						<span class="text-sm"
							>A {spec.noun}
							{FIRE_ON_CLAUSE[fireOn as FireOn] ?? fireOnLabel(fireOn).toLowerCase()}</span
						>
						<QueryChip {dimension} {query} class="max-w-full" />
					{:else}
						{#each actions as action (action.label)}
							<span class="truncate text-sm">{action.label}</span>
							<span class="truncate text-xs text-muted-foreground">{action.detail}</span>
						{/each}
						{#if actions.length === 0}
							<span class="text-sm text-muted-foreground">No action</span>
						{/if}
					{/if}
				</span>
			</div>
			{#if index < NODES.length - 1}
				<span
					class="flex shrink-0 items-center justify-center text-muted-foreground"
					aria-hidden="true"
				>
					<ArrowDown class="size-4 sm:hidden" />
					<ArrowRight class="hidden size-4 sm:block" />
				</span>
			{/if}
		</li>
	{/each}
</ol>
