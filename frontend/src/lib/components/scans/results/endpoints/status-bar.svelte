<script lang="ts">
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { STATUS_CLASS_FILL, STATUS_CLASS_LABELS } from '$lib/config/endpoints';

	interface Props {
		mix: Record<string, number>;
		total: number;
	}

	let { mix, total }: Props = $props();
	const ORDER = ['2xx', '3xx', '4xx', '5xx', 'none'];
	let parts = $derived(ORDER.filter((k) => (mix[k] ?? 0) > 0).map((k) => ({ k, n: mix[k] })));
</script>

<Tooltip.Root>
	<Tooltip.Trigger class="block w-full">
		<span class="flex h-1 w-full overflow-hidden rounded-full bg-muted">
			{#each parts as p (p.k)}
				<span
					class="h-full"
					style="width:{(p.n / Math.max(total, 1)) * 100}%;background:{STATUS_CLASS_FILL[p.k]}"
				></span>
			{/each}
		</span>
	</Tooltip.Trigger>
	<Tooltip.Content>
		<div class="space-y-0.5 text-xs">
			{#each parts as p (p.k)}
				<div class="flex items-center gap-2">
					<span class="size-1.5 rounded-full" style="background:{STATUS_CLASS_FILL[p.k]}"></span>
					<span>{STATUS_CLASS_LABELS[p.k] ?? p.k}</span>
					<span class="ml-auto tabular-nums">{p.n}</span>
				</div>
			{/each}
		</div>
	</Tooltip.Content>
</Tooltip.Root>
