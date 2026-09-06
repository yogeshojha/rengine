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
	import Play from '@lucide/svelte/icons/play';
	import SearchIcon from '@lucide/svelte/icons/search';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import { targetsApi } from '$lib/api/targets';
	import type { Target as TargetEntity } from '$lib/types/target';

	let { onAddTarget, onScan }: { onAddTarget: () => void; onScan: (value: string) => void } =
		$props();

	let commandOpen = $state(false);
	let searchQuery = $state('');
	let searchResults = $state<TargetEntity[]>([]);
	let searching = $state(false);
	let scanCandidate = $state<string | null>(null);

	const isMac = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform);
	const searchShortcut = isMac ? '⌘K' : 'Ctrl+K';

	$effect(() => {
		const q = searchQuery.trim();
		if (q.length < 2) {
			searchResults = [];
			scanCandidate = null;
			searching = false;
			return;
		}
		searching = true;
		const t = setTimeout(async () => {
			try {
				const [results, check] = await Promise.all([
					targetsApi.searchByValue(q),
					/\s/.test(q)
						? Promise.resolve(null)
						: targetsApi.validate({ target_value: q }).catch(() => null)
				]);
				searchResults = results;
				scanCandidate = check?.valid ? check.target_value || q : null;
			} catch {
				searchResults = [];
				scanCandidate = null;
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
			scanCandidate = null;
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
					{:else}
						{#if scanCandidate}
							{@const candidate = scanCandidate}
							<Command.Group heading="Scan">
								<Command.Item
									value="scan:{candidate}"
									onSelect={() => {
										commandOpen = false;
										onScan(candidate);
									}}
								>
									<Play class="mr-2 h-4 w-4 shrink-0" />
									<span class="truncate">
										Scan <span class="font-mono text-xs">{candidate}</span>
									</span>
								</Command.Item>
							</Command.Group>
						{/if}
						{#if searchResults.length === 0}
							{#if !scanCandidate}
								<div class="py-6 text-center text-sm text-muted-foreground">No targets found.</div>
							{/if}
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
								Add organization
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
							<span>New scan engine</span>
						</Command.Item>
						<Command.Item
							onSelect={() => {
								commandOpen = false;
								goto(ROUTES.contexts);
							}}
						>
							<Layers class="mr-2 h-4 w-4" />
							<span>New scan context</span>
						</Command.Item>
					</Command.Group>
				{/if}
			</Command.List>
		</Command.Root>
	</Dialog.Content>
</Dialog.Root>
