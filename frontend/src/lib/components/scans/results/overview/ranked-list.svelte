<script lang="ts">
	import type { Snippet } from 'svelte';
	import { Badge } from '$lib/components/ui/badge';

	export interface RankedRow {
		key: string;
		label: string;
		count: number;
		sub?: string;
		mono?: boolean;
		badge?: string;
		meta?: string;
		filter?: string;
	}

	interface Props {
		rows: RankedRow[];
		base: number;
		onSelect?: (filter: string) => void;
		icon?: Snippet<[RankedRow]>;
	}

	let { rows, base, onSelect, icon }: Props = $props();

	const MIN_METER = 1.5;

	const share = (n: number) => (base > 0 ? (n / base) * 100 : 0);
	const shareLabel = (n: number) => {
		const p = share(n);
		return p > 0 && p < 1 ? '<1%' : `${Math.round(p)}%`;
	};
</script>

<ul class="-mx-2 flex flex-col gap-0.5">
	{#each rows as r (r.key)}
		{@const clickable = !!r.filter && !!onSelect}
		<li>
			<button
				type="button"
				class="group flex w-full flex-col gap-1.5 rounded-md px-2 py-1.5 text-left transition-colors {clickable
					? 'cursor-pointer hover:bg-muted/50'
					: 'cursor-default'}"
				disabled={!clickable}
				onclick={() => r.filter && onSelect?.(r.filter)}
			>
				<span class="flex w-full items-center gap-2">
					{#if icon}
						<span class="flex h-5 w-4 shrink-0 items-center justify-center">
							{@render icon(r)}
						</span>
					{/if}
					<span class="flex min-w-0 flex-1 flex-col">
						<span
							class="truncate leading-5 {r.mono ? 'font-mono text-xs' : 'text-sm'}"
							title={r.label}
						>
							{r.label}
						</span>
						{#if r.sub}
							<span class="truncate text-xs leading-4 text-muted-foreground">{r.sub}</span>
						{/if}
					</span>
					{#if r.badge}
						<span class="flex h-5 shrink-0 items-center">
							<Badge variant="warning" class="h-4 px-1 text-[10px]">{r.badge}</Badge>
						</span>
					{/if}
					<span class="text-sm font-medium tabular-nums">{r.count.toLocaleString()}</span>
					<span class="w-9 shrink-0 text-right text-xs text-muted-foreground tabular-nums">
						{shareLabel(r.count)}
					</span>
				</span>
				<span class="block h-1 w-full overflow-hidden rounded-full bg-muted" aria-hidden="true">
					<span
						class="block h-full rounded-full bg-chart-1"
						style="width:{Math.max(MIN_METER, share(r.count))}%"
					></span>
				</span>
			</button>
		</li>
	{/each}
</ul>
