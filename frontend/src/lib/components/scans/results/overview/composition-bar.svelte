<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip';

	export interface Segment {
		key: string;
		label: string;
		count: number;
		color: string;
		filter?: string;
	}

	interface Props {
		segments: Segment[];
		total: number;
		label: string;
		onSelect?: (filter: string) => void;
	}

	let { segments, total, label, onSelect }: Props = $props();

	const MIN_BAR_SEGMENTS = 2;

	const pct = (n: number) => (total > 0 ? (n / total) * 100 : 0);
	const pctLabel = (n: number) => {
		const p = pct(n);
		return p > 0 && p < 1 ? '<1%' : `${Math.round(p)}%`;
	};
</script>

<div class="flex flex-col gap-3">
	{#if segments.length >= MIN_BAR_SEGMENTS}
		<div class="flex h-1.5 w-full gap-0.5" role="img" aria-label={label}>
			{#each segments as s (s.key)}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							{#if s.filter && onSelect}
								<button
									{...props}
									type="button"
									class="relative h-full min-w-1.5 cursor-pointer rounded-full transition-opacity before:absolute before:inset-x-0 before:-inset-y-1 before:content-[''] hover:opacity-75"
									style="flex:{s.count} 1 0;background:{s.color}"
									aria-label="{s.label}, {s.count}"
									onclick={() => onSelect(s.filter!)}
								></button>
							{:else}
								<span
									{...props}
									class="h-full min-w-1.5 rounded-full"
									style="flex:{s.count} 1 0;background:{s.color}"
								></span>
							{/if}
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content side="top" class="tabular-nums">
						{s.label} · {s.count.toLocaleString()} · {pctLabel(s.count)}
					</Tooltip.Content>
				</Tooltip.Root>
			{/each}
		</div>
	{/if}

	<ul class="-mx-1.5 flex flex-col">
		{#each segments as s (s.key)}
			<li>
				{#if s.filter && onSelect}
					<button
						type="button"
						class="flex w-full cursor-pointer items-center gap-2.5 rounded-md px-1.5 py-1 text-left transition-colors hover:bg-muted/50"
						onclick={() => onSelect(s.filter!)}
					>
						{@render row(s)}
					</button>
				{:else}
					<div class="flex w-full items-center gap-2.5 px-1.5 py-1">
						{@render row(s)}
					</div>
				{/if}
			</li>
		{/each}
	</ul>
</div>

{#snippet row(s: Segment)}
	<span class="size-2 shrink-0 rounded-[2px]" style="background:{s.color}" aria-hidden="true"
	></span>
	<span class="min-w-0 flex-1 text-sm leading-5">{s.label}</span>
	<span class="text-sm font-medium tabular-nums">{s.count.toLocaleString()}</span>
	<span class="w-9 shrink-0 text-right text-xs text-muted-foreground tabular-nums">
		{pctLabel(s.count)}
	</span>
{/snippet}
