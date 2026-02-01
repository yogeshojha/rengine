<script lang="ts">
	import { Play, Trash2, X } from 'lucide-svelte';

	interface Props {
		selectedCount: number;
		onScan: () => void;
		onDelete: () => void;
		onClear: () => void;
	}

	let { selectedCount, onScan, onDelete, onClear }: Props = $props();
</script>
<div
	class="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 transition-all duration-300 ease-out {selectedCount
		> 0
		? 'translate-y-0 opacity-100'
		: 'translate-y-3 opacity-0 pointer-events-none'}"
>
	<div
		class="flex items-center gap-0.5 bg-gray-900/80 backdrop-blur-xl backdrop-saturate-180 border border-white/10 rounded-2xl shadow-xl shadow-black/30 p-1.5"
	>
		<div class="flex items-center px-2.5 py-1.5">
			<span class="text-xs font-medium text-gray-400 tabular-nums">
				{selectedCount}
				{selectedCount === 1 ? 'target' : 'targets'} selected
			</span>
		</div>

		<div class="w-px h-4 bg-white/10 self-center mx-0.5"></div>

		<button
			class="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-white/10 transition-colors"
			onclick={onScan}
		>
			<Play class="h-3.5 w-3.5 text-blue-400" />
			<span class="text-sm text-gray-100 font-medium">Scan</span>
		</button>

		<button
			class="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
			onclick={onDelete}
		>
			<Trash2 class="h-3.5 w-3.5 text-red-400" />
			<span class="text-sm text-red-400 font-medium">Delete</span>
		</button>
		<div class="w-px h-4 bg-white/10 self-center mx-0.5"></div>
		<button
			class="flex items-center justify-center w-7 h-7 rounded-lg hover:bg-white/10 transition-colors"
			onclick={onClear}
		>
			<X class="h-3.5 w-3.5 text-gray-500" />
		</button>
	</div>
</div>
