<script lang="ts">
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import Crosshair from '@lucide/svelte/icons/crosshair';
	import Building from '@lucide/svelte/icons/building';
	import Cog from '@lucide/svelte/icons/cog';
	import Layers from '@lucide/svelte/icons/layers';
	import SearchIcon from '@lucide/svelte/icons/search';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import { targetsApi } from '$lib/api/targets';
	import type { Target as TargetEntity } from '$lib/types/target';

	let { onAddTarget }: { onAddTarget: () => void } = $props();

	let commandOpen = $state(false);
	let searchQuery = $state('');
	let searchResults = $state<TargetEntity[]>([]);
	let searching = $state(false);

	const isMac = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform);
	const searchShortcut = isMac ? '⌘K' : 'Ctrl+K';

	$effect(() => {
		const q = searchQuery.trim();
		if (q.length < 2) {
			searchResults = [];
			searching = false;
			return;
		}
		searching = true;
		const t = setTimeout(async () => {
			try {
				searchResults = await targetsApi.searchByValue(q);
			} catch {
				searchResults = [];
			} finally {
				searching = false;
			}
		}, 250);
		return () => clearTimeout(t);
	});

	$effect(() => {
		if (!commandOpen) {
			searchQuery = '';
			searchResults = [];
		}
	});

	$effect(() => {
		const handleKeydown = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
				e.preventDefault();
				commandOpen = !commandOpen;
			}
		};
		document.addEventListener('keydown', handleKeydown);
		return () => document.removeEventListener('keydown', handleKeydown);
	});
</script>

<Button
	variant="outline"
	class="relative h-9 w-full justify-start rounded-md text-sm text-muted-foreground sm:w-64 md:w-80"
	onclick={() => (commandOpen = true)}
>
	<SearchIcon class="mr-2 h-4 w-4" />
	<span>Search…</span>
	<kbd
		class="pointer-events-none absolute right-1.5 top-1.5 hidden h-6 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex"
	>
		{searchShortcut}
	</kbd>
</Button>

<Dialog.Root bind:open={commandOpen}>
	<Dialog.Content class="overflow-hidden p-0 shadow-lg sm:max-w-[550px]">
		<Command.Root shouldFilter={false} class="[&_[data-cmd-input-wrapper]]:border-b">
			<Command.Input bind:value={searchQuery} placeholder="Search targets or run an action…" />
			<Command.List>
				{#if searchQuery.trim().length >= 2}
					{#if searching}
						<div class="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
							<Spinner class="size-4" /> Searching…
						</div>
					{:else if searchResults.length === 0}
						<div class="py-6 text-center text-sm text-muted-foreground">No targets found.</div>
					{:else}
						<Command.Group heading="Targets">
							{#each searchResults as t (t.id)}
								<Command.Item
									value={t.id}
									onSelect={() => {
										commandOpen = false;
										goto(ROUTES.target(t.id));
									}}
								>
									<Crosshair class="mr-2 h-4 w-4 shrink-0" />
									<span class="truncate">{t.target_value}</span>
								</Command.Item>
							{/each}
						</Command.Group>
					{/if}
				{:else}
					<Command.Group heading="Quick actions">
						<Command.Item
							onSelect={() => {
								commandOpen = false;
								onAddTarget();
							}}
						>
							<Crosshair class="mr-2 h-4 w-4" />
							<span>Add target</span>
						</Command.Item>
						<Command.Item disabled class="justify-between">
							<span class="flex items-center">
								<Building class="mr-2 h-4 w-4" />
								Add Organization
							</span>
							<Badge variant="secondary" class="text-[10px]">Soon</Badge>
						</Command.Item>
						<Command.Item
							onSelect={() => {
								commandOpen = false;
								goto(ROUTES.engines);
							}}
						>
							<Cog class="mr-2 h-4 w-4" />
							<span>New Scan Engine</span>
						</Command.Item>
						<Command.Item
							onSelect={() => {
								commandOpen = false;
								goto(ROUTES.contexts);
							}}
						>
							<Layers class="mr-2 h-4 w-4" />
							<span>New Scan Context</span>
						</Command.Item>
					</Command.Group>
				{/if}
			</Command.List>
		</Command.Root>
	</Dialog.Content>
</Dialog.Root>
