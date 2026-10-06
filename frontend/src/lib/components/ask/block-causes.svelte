<script lang="ts">
	import { linkScan } from './link-scope';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Server from '@lucide/svelte/icons/server';
	import Hint from '$lib/components/hint.svelte';
	import { blockHref } from './block-columns';
	import { surfaceSpec } from '$lib/config/surface';
	import { cn } from '$lib/utils.js';
	import type { BlockCause, BlockCauses } from '$lib/types/ask';

	interface Props {
		dimension: string;
		causes: BlockCauses;
		total: number;
		capped?: boolean;
		scopeValues: string[] | null;
		disabled?: boolean;
		onCause?: (cause: BlockCause) => void;
	}

	let {
		dimension,
		causes,
		total,
		capped = false,
		scopeValues,
		disabled = false,
		onCause
	}: Props = $props();

	const scan = linkScan();

	let spec = $derived(surfaceSpec(dimension));
	let Icon = $derived(causes.address ? Server : spec?.icon);
	let mono = $derived(causes.mono);
	let more = $derived(causes.total_groups - causes.groups.length);
	let noun = $derived(spec?.nounPlural ?? 'rows');
	let openLabel = $derived(`Open in ${spec?.label ?? 'results'}`);

	function askLabel(cause: BlockCause): string {
		const where = `${causes.prep} ${cause.label}`;
		return cause.count === 1
			? `Ask about the ${spec?.noun ?? 'row'} ${where}`
			: `Ask about the ${cause.count.toLocaleString()} ${noun} ${where}`;
	}

	let scale = $derived(
		capped ? Math.max(1, ...causes.groups.map((c) => c.count)) : Math.max(1, total)
	);

	function share(count: number): string {
		return `${Math.max(2, Math.min(100, (count / scale) * 100))}%`;
	}
</script>

<ul class="flex flex-col divide-y">
	{#each causes.groups as cause (cause.value)}
		{@const href = blockHref(dimension, cause.query, scopeValues, scan())}
		<li
			class="relative grid grid-cols-[1.75rem_minmax(0,1fr)_auto_1.5rem] items-center gap-3 px-4 py-2.5 hover:bg-muted/40 sm:grid-cols-[1.75rem_minmax(0,1fr)_auto_minmax(3rem,7rem)_1.5rem]"
		>
			<button
				type="button"
				{disabled}
				class="absolute inset-0 rounded-none outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default"
				onclick={() => onCause?.(cause)}
				aria-label={askLabel(cause)}
			></button>
			<span
				class="pointer-events-none flex size-7 items-center justify-center rounded-md bg-muted text-muted-foreground"
			>
				{#if Icon}<Icon class="size-3.5" />{/if}
			</span>
			<span class="pointer-events-none flex min-w-0 flex-col gap-0.5">
				<span class="flex min-w-0 flex-wrap items-baseline gap-x-2">
					<span
						class={cn(
							'wrap-anywhere',
							mono ? 'font-mono text-xs font-semibold' : 'text-sm font-medium'
						)}>{cause.label}</span
					>
					{#if cause.who}
						<span class="min-w-0 truncate text-xs text-muted-foreground">{cause.who}</span>
					{/if}
				</span>
				{#if cause.details.length}
					<span class="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
						{#each cause.details as d, i (i)}
							{#if d.hint}
								<Hint text={d.hint}>
									{#snippet child(props)}
										<span
											{...props}
											class="pointer-events-auto relative font-mono text-2xs wrap-anywhere"
											>{d.label}<span class="text-muted-foreground/70"> ×{d.count}</span></span
										>
									{/snippet}
								</Hint>
							{:else}
								<span class="text-2xs wrap-anywhere"
									>{d.label}<span class="text-muted-foreground/70"> ×{d.count}</span></span
								>
							{/if}
						{/each}
					</span>
				{/if}
			</span>
			<span class="pointer-events-none text-right text-base font-semibold tabular-nums"
				>{cause.count.toLocaleString()}</span
			>
			<span
				class="pointer-events-none hidden h-1.5 overflow-hidden rounded-full bg-muted sm:block"
				aria-hidden="true"
			>
				<span class="block h-full rounded-full bg-series" style:width={share(cause.count)}></span>
			</span>
			{#if href}
				<Hint text={openLabel}>
					{#snippet child(props)}
						<a
							{...props}
							{href}
							class="relative inline-flex size-6 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
							aria-label={openLabel}
						>
							<ArrowUpRight class="size-3.5" />
						</a>
					{/snippet}
				</Hint>
			{:else}
				<span></span>
			{/if}
		</li>
	{/each}
</ul>
{#if more > 0}
	<p class="m-0 border-t px-4 py-2 text-xs text-muted-foreground">
		{more.toLocaleString()} more {more === 1 ? causes.one : causes.many}
	</p>
{/if}
