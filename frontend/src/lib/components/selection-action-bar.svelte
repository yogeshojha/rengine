<script lang="ts">
	import type { Snippet } from 'svelte';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';

	interface Props {
		selectedCount: number;
		noun: string;
		nounPlural?: string;
		onClear: () => void;
		children: Snippet;
	}

	let { selectedCount, noun, nounPlural, onClear, children }: Props = $props();

	const label = $derived(selectedCount === 1 ? noun : (nounPlural ?? `${noun}s`));
</script>

<div
	class="fixed bottom-8 left-1/2 z-50 max-w-[calc(100vw-1rem)] -translate-x-1/2 transition-all duration-300 ease-out {selectedCount >
	0
		? 'translate-y-0 opacity-100'
		: 'pointer-events-none translate-y-3 opacity-0'}"
	role="region"
	aria-label="Selection actions"
	aria-hidden={selectedCount === 0}
>
	<div
		class="flex flex-wrap items-center justify-center gap-0.5 gap-y-1 rounded-2xl border border-border bg-popover p-1.5 text-popover-foreground shadow-xl shadow-black/30 backdrop-blur-xl backdrop-saturate-180"
	>
		<div class="flex items-center px-2.5 py-1.5">
			<span class="text-xs font-medium tabular-nums text-muted-foreground">
				{selectedCount}
				{label} selected
			</span>
		</div>

		<Separator orientation="vertical" class="mx-0.5 h-4 self-center" />

		{@render children()}

		<Separator orientation="vertical" class="mx-0.5 h-4 self-center" />
		<Button
			variant="ghost"
			size="icon-sm"
			class="text-muted-foreground"
			aria-label="Clear selection"
			onclick={onClear}
		>
			<X class="h-3.5 w-3.5" />
		</Button>
	</div>
</div>
