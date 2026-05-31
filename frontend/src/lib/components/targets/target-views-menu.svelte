<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Bookmark, Plus, Trash2 } from 'lucide-svelte';
	import { browser } from '$app/environment';

	interface Props {
		currentQuery: string;
		onApply: (query: string) => void;
	}

	let { currentQuery, onApply }: Props = $props();

	interface SavedView {
		name: string;
		query: string;
	}

	const KEY = 'targets:views';

	let views = $state<SavedView[]>(load());

	function load(): SavedView[] {
		if (!browser) return [];
		try {
			return JSON.parse(localStorage.getItem(KEY) ?? '[]');
		} catch {
			return [];
		}
	}

	function persist() {
		if (browser) localStorage.setItem(KEY, JSON.stringify(views));
	}

	function saveCurrent() {
		const name = window.prompt('Save this view as');
		if (!name?.trim()) return;
		views = [
			...views.filter((v) => v.name !== name.trim()),
			{ name: name.trim(), query: currentQuery }
		];
		persist();
	}

	function remove(e: MouseEvent, view: SavedView) {
		e.stopPropagation();
		views = views.filter((v) => v !== view);
		persist();
	}
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="outline" size="sm" class="h-9 gap-2">
				<Bookmark class="h-4 w-4" />
				<span class="hidden sm:inline">Views</span>
			</Button>
		{/snippet}
	</DropdownMenu.Trigger>
	<DropdownMenu.Content align="end" class="w-56">
		<DropdownMenu.Item onclick={saveCurrent} class="gap-2">
			<Plus class="h-4 w-4" />
			Save current view
		</DropdownMenu.Item>
		{#if views.length > 0}
			<DropdownMenu.Separator />
			<DropdownMenu.Label>Saved</DropdownMenu.Label>
			{#each views as view (view.name)}
				<DropdownMenu.Item onclick={() => onApply(view.query)} class="justify-between gap-2">
					<span class="truncate">{view.name}</span>
					<button
						class="text-muted-foreground hover:text-destructive"
						onclick={(e) => remove(e, view)}
					>
						<Trash2 class="h-3.5 w-3.5" />
					</button>
				</DropdownMenu.Item>
			{/each}
		{/if}
	</DropdownMenu.Content>
</DropdownMenu.Root>
