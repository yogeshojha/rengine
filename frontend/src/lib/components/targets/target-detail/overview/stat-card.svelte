<script lang="ts">
	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { TrendingUp, TrendingDown } from 'lucide-svelte';
	import type { Component } from 'svelte';

	type DeltaContext = 'neutral' | 'inverse';

	interface Props {
		label: string;
		value: number;
		unit?: string;
		icon: Component;
		delta?: number | null;
		deltaContext?: DeltaContext;
		previousValue?: number | null;
		accent?: 'default' | 'danger' | 'success';
	}

	let {
		label,
		value,
		unit = '',
		icon: Icon,
		delta = null,
		deltaContext = 'neutral',
		previousValue = null,
		accent = 'default'
	}: Props = $props();

	const deltaDisplay = $derived.by(() => {
		if (delta === null || delta === 0) return null;
		const isPositive = delta > 0;
		let color: string;
		if (deltaContext === 'inverse') {
			color = isPositive
				? 'text-red-600 dark:text-red-400 bg-red-500/10 border-red-500/20'
				: 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
		} else {
			color = isPositive
				? 'text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20'
				: 'text-muted-foreground bg-muted border-border';
		}
		return {
			text: isPositive ? `+${delta}` : `${delta}`,
			color,
			icon: isPositive ? TrendingUp : TrendingDown
		};
	});

	const accentColor = $derived.by(() => {
		switch (accent) {
			case 'danger':
				return 'bg-red-500/60';
			case 'success':
				return 'bg-emerald-500/60';
			default:
				return 'bg-border';
		}
	});
</script>

<Card.Root class="overflow-hidden">
	<div class="flex">
		<div class="w-[3px] shrink-0 {accentColor}"></div>
		<Card.Content class="flex-1 py-3 px-4 space-y-1">
			<!-- Icon lavel and horizontal subtle line -->
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-1.5 text-xs text-muted-foreground">
					<Icon class="h-3.5 w-3.5" />
					<span class="font-medium">{label}</span>
				</div>
				{#if deltaDisplay}
					{@const DeltaIcon = deltaDisplay.icon}
					<Badge
						variant="outline"
						class="h-[18px] px-1 text-[10px] font-semibold gap-0.5 rounded-sm {deltaDisplay.color}"
					>
						<DeltaIcon class="h-2.5 w-2.5" />
						{deltaDisplay.text}
					</Badge>
				{/if}
			</div>

			<!-- stat value + growth  -->
			<div class="flex items-baseline gap-2">
				<span class="text-xl font-semibold tracking-tight tabular-nums">
					{value.toLocaleString()}{#if unit}<span class="text-xs font-normal text-muted-foreground ml-0.5">{unit}</span>{/if}
				</span>
				{#if previousValue !== null}
					<span class="text-[11px] text-muted-foreground">
						· vs {previousValue.toLocaleString()}{unit ? ` ${unit}` : ''} last scan
					</span>
				{/if}
			</div>
		</Card.Content>
	</div>
</Card.Root>
