<script lang="ts">
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { TIMELINE_WINDOWS } from '$lib/config/timeline';

	interface Props {
		value: number;
		onChange: (scans: number) => void;
	}

	let { value, onChange }: Props = $props();
</script>

<div class="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
	<span>Last</span>
	<ToggleGroup.Root
		type="single"
		variant="outline"
		size="sm"
		value={String(value)}
		onValueChange={(v) => v && onChange(Number(v))}
		aria-label="Scans shown"
	>
		{#each TIMELINE_WINDOWS as n (n)}
			<ToggleGroup.Item
				value={String(n)}
				aria-label="Last {n} scans"
				class="h-7 px-2.5 text-xs font-normal tabular-nums"
			>
				{n}
			</ToggleGroup.Item>
		{/each}
	</ToggleGroup.Root>
	<span>scans</span>
</div>
