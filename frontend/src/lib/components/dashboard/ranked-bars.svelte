<script lang="ts" module>
	export interface BarRow {
		key: string;
		label: string;
		count: number;
		sub?: string;
		href?: string;
		mono?: boolean;
		tone?: string;
	}
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import Hint from '$lib/components/hint.svelte';

	interface Props {
		rows: BarRow[];
		base?: number;
		icon?: Snippet<[BarRow]>;
		dense?: boolean;
	}

	let { rows, base, icon, dense = false }: Props = $props();

	let max = $derived(Math.max(1, base ?? 0, ...rows.map((r) => r.count)));
	const MIN = 1.5;
	const width = (n: number) => Math.max(MIN, (n / max) * 100);
</script>

<ul class="flex flex-col {dense ? 'gap-0.5' : 'gap-1'}">
	{#each rows as r (r.key)}
		<li>
			<svelte:element
				this={r.href ? 'a' : 'div'}
				href={r.href}
				class="group flex items-center gap-2.5 rounded-md px-2 py-1 transition-colors {r.href
					? 'hover:bg-muted/50'
					: ''} -mx-2"
			>
				{#if icon}
					<span class="flex h-5 w-4 shrink-0 items-center justify-center">{@render icon(r)}</span>
				{/if}
				<span class="flex min-w-0 flex-1 flex-col gap-1">
					<span class="flex items-baseline justify-between gap-3">
						<Hint text={r.sub ? `${r.label} · ${r.sub}` : r.label}>
							{#snippet child(props)}
								<span
									{...props}
									class="truncate leading-5 {r.mono ? 'font-mono text-xs' : 'text-sm'} {r.href
										? 'group-hover:text-foreground'
										: ''}"
								>
									{r.label}
									{#if r.sub}<span class="ml-1.5 font-sans text-2xs text-muted-foreground"
											>{r.sub}</span
										>{/if}
								</span>
							{/snippet}
						</Hint>
						<span class="shrink-0 text-xs font-medium tabular-nums">{r.count.toLocaleString()}</span
						>
					</span>
					<span class="h-1 w-full overflow-hidden rounded-full bg-muted">
						<span
							class="block h-full rounded-full"
							style="width:{width(r.count)}%;background:{r.tone ?? 'var(--series)'}"
						></span>
					</span>
				</span>
			</svelte:element>
		</li>
	{/each}
</ul>
