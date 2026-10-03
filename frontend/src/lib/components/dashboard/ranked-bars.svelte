<script lang="ts" module>
	export interface BarRow {
		key: string;
		label: string;
		count: number;
		sub?: string;
		href?: string;
		tone?: string;
	}
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import Hint from '$lib/components/hint.svelte';
	import { safeHref } from '$lib/utilities/links';

	interface Props {
		rows: BarRow[];
		icon?: Snippet<[BarRow]>;
	}

	let { rows, icon }: Props = $props();

	let max = $derived(Math.max(1, ...rows.map((r) => r.count)));
	const MIN = 1.5;
	const width = (n: number) => Math.max(MIN, (n / max) * 100);
</script>

{#snippet body(r: BarRow)}
	{#if icon}
		<span class="flex h-5 w-4 shrink-0 items-center justify-center">{@render icon(r)}</span>
	{/if}
	<span class="flex min-w-0 flex-1 flex-col gap-1">
		<span class="flex items-baseline justify-between gap-3">
			<Hint text={r.sub ? `${r.label} · ${r.sub}` : r.label}>
				{#snippet child(props)}
					<span
						{...props}
						class="truncate text-sm leading-5 {r.href ? 'group-hover:text-foreground' : ''}"
					>
						{r.label}
						{#if r.sub}<span class="ml-1.5 font-sans text-2xs text-muted-foreground">{r.sub}</span
							>{/if}
					</span>
				{/snippet}
			</Hint>
			<span class="shrink-0 text-xs font-medium tabular-nums">{r.count.toLocaleString()}</span>
		</span>
		<span class="h-1 w-full overflow-hidden rounded-full bg-muted">
			<span
				class="block h-full rounded-full"
				style="width:{width(r.count)}%;background:{r.tone ?? 'var(--series)'}"
			></span>
		</span>
	</span>
{/snippet}

<ul class="flex flex-col gap-0.5">
	{#each rows as r (r.key)}
		<li>
			{#if r.href}
				<a
					href={safeHref(r.href)}
					class="group -mx-2 flex items-center gap-2.5 rounded-md px-2 py-1 transition-colors hover:bg-muted/50"
				>
					{@render body(r)}
				</a>
			{:else}
				<div class="group -mx-2 flex items-center gap-2.5 rounded-md px-2 py-1 transition-colors">
					{@render body(r)}
				</div>
			{/if}
		</li>
	{/each}
</ul>
