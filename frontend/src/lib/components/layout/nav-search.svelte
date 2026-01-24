<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import Search from 'lucide-svelte/icons/search';

	function handleSearch() {
        // TODO: integrate with search component
		console.log('Open search');
		window.dispatchEvent(new CustomEvent('open-search'));
	}

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
			e.preventDefault();
			handleSearch();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<Sidebar.Group class="py-0">
	<Sidebar.Menu>
		<Sidebar.MenuItem>
			<Sidebar.MenuButton onclick={handleSearch} tooltipContent="Search (⌘K)">
				{#snippet child({ props })}
					<button {...props} class="flex w-full items-center gap-2">
						<Search class="size-4" />
						<span class="flex-1 text-start">Search</span>
						<kbd
							class="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex"
						>
							<span class="text-xs">⌘</span>K
						</kbd>
					</button>
				{/snippet}
			</Sidebar.MenuButton>
		</Sidebar.MenuItem>
	</Sidebar.Menu>
</Sidebar.Group>