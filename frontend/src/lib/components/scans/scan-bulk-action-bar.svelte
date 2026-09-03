<script lang="ts">
	import Play from '@lucide/svelte/icons/play';
	import Ban from '@lucide/svelte/icons/ban';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';

	interface Props {
		selectedCount: number;
		liveCount: number;
		targetCount: number;
		onRescan: () => void;
		onCancel: () => void;
		onDelete: () => void;
		onClear: () => void;
	}

	let { selectedCount, liveCount, targetCount, onRescan, onCancel, onDelete, onClear }: Props =
		$props();
</script>

<div
	class="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 max-w-[calc(100vw-1rem)] transition-all duration-300 ease-out {selectedCount >
	0
		? 'translate-y-0 opacity-100'
		: 'translate-y-3 opacity-0 pointer-events-none'}"
>
	<div
		class="flex flex-wrap items-center justify-center gap-0.5 gap-y-1 bg-popover text-popover-foreground backdrop-blur-xl backdrop-saturate-180 border border-border rounded-2xl shadow-xl shadow-black/30 p-1.5"
	>
		<div class="flex items-center px-2.5 py-1.5">
			<span class="text-xs font-medium text-muted-foreground tabular-nums">
				{selectedCount}
				{selectedCount === 1 ? 'scan' : 'scans'} selected
			</span>
		</div>

		<Separator orientation="vertical" class="h-4 self-center mx-0.5" />

		{#if targetCount > 0}
			<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={onRescan}>
				<Play class="h-3.5 w-3.5 text-muted-foreground" />
				Re-scan {targetCount}
				{targetCount === 1 ? 'target' : 'targets'}
			</Button>
		{/if}

		{#if liveCount > 0}
			<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={onCancel}>
				<Ban class="h-3.5 w-3.5 text-muted-foreground" />
				Cancel {liveCount}
			</Button>
		{/if}

		<Button
			variant="ghost"
			size="sm"
			class="gap-2 font-medium text-destructive hover:bg-destructive/10 hover:text-destructive"
			onclick={onDelete}
		>
			<Trash2 class="h-3.5 w-3.5" />
			Delete
		</Button>

		<Separator orientation="vertical" class="h-4 self-center mx-0.5" />
		<Button variant="ghost" size="icon-sm" class="text-muted-foreground" onclick={onClear}>
			<X class="h-3.5 w-3.5" />
		</Button>
	</div>
</div>
