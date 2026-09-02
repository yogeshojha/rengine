<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Dialog from '$lib/components/ui/dialog';
	import ConfirmDialog from '@/components/confirm-dialog.svelte';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import Plus from '@lucide/svelte/icons/plus';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Check from '@lucide/svelte/icons/check';
	import { browser } from '$app/environment';
	import { toast } from 'svelte-sonner';

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
	let saveOpen = $state(false);
	let newName = $state('');
	let pendingDelete = $state<SavedView | null>(null);
	let menuOpen = $state(false);

	let trimmed = $derived(newName.trim());
	let canSave = $derived(trimmed.length > 0);
	let isOverwrite = $derived(canSave && views.some((v) => v.name === trimmed));

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

	function confirmSave(e: Event) {
		e.preventDefault();
		if (!canSave) return;
		const overwrite = isOverwrite;
		views = [...views.filter((v) => v.name !== trimmed), { name: trimmed, query: currentQuery }];
		persist();
		saveOpen = false;
		toast.success(overwrite ? `View "${trimmed}" updated` : `View "${trimmed}" saved`);
	}

	function confirmDelete() {
		if (!pendingDelete) return;
		const name = pendingDelete.name;
		views = views.filter((v) => v !== pendingDelete);
		persist();
		pendingDelete = null;
		toast.success(`View "${name}" deleted`);
	}

	$effect(() => {
		if (!saveOpen) newName = '';
	});
</script>

<DropdownMenu.Root bind:open={menuOpen}>
	<DropdownMenu.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="outline" size="sm" class="h-9 gap-2">
				<Bookmark class="h-4 w-4" />
				<span class="hidden sm:inline">Views</span>
			</Button>
		{/snippet}
	</DropdownMenu.Trigger>
	<DropdownMenu.Content align="end" class="w-56">
		<DropdownMenu.Item onclick={() => (saveOpen = true)} class="gap-2">
			<Plus class="h-4 w-4" />
			Save current view
		</DropdownMenu.Item>
		{#if views.length > 0}
			<DropdownMenu.Separator />
			<DropdownMenu.Label>Saved</DropdownMenu.Label>
			{#each views as view (view.name)}
				{@const active = view.query === currentQuery}
				<div class="flex items-center gap-1 px-1 py-0.5">
					<button
						type="button"
						onclick={() => {
							menuOpen = false;
							onApply(view.query);
						}}
						aria-current={active ? 'true' : undefined}
						class="flex h-9 flex-1 items-center gap-2 truncate rounded-sm px-2 text-left text-sm hover:bg-accent"
					>
						<Check class="h-4 w-4 shrink-0 {active ? 'opacity-100' : 'opacity-0'}" />
						<span class="truncate {active ? 'font-medium' : ''}">{view.name}</span>
					</button>
					<button
						type="button"
						aria-label="Delete view {view.name}"
						class="flex size-9 shrink-0 items-center justify-center rounded-sm text-muted-foreground hover:bg-accent hover:text-destructive"
						onclick={() => {
							menuOpen = false;
							pendingDelete = view;
						}}
					>
						<Trash2 class="h-3.5 w-3.5" />
					</button>
				</div>
			{/each}
		{/if}
	</DropdownMenu.Content>
</DropdownMenu.Root>

<ConfirmDialog
	open={!!pendingDelete}
	title="Delete this view?"
	description={`Delete the saved view "${pendingDelete?.name ?? ''}"? This removes the saved filter only — your targets are not affected.`}
	confirmLabel="Delete view"
	destructive
	onOpenChange={(o) => {
		if (!o) pendingDelete = null;
	}}
	onConfirm={confirmDelete}
/>

<Dialog.Root bind:open={saveOpen}>
	<Dialog.Content class="w-[calc(100%-2rem)] sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Save view</Dialog.Title>
			<Dialog.Description>Name this filter so you can reapply it later.</Dialog.Description>
		</Dialog.Header>
		<form onsubmit={confirmSave} class="space-y-4">
			<div class="space-y-2">
				<Label for="view-name">View name</Label>
				<Input id="view-name" bind:value={newName} placeholder="e.g. Live web hosts" autofocus />
			</div>
			<Dialog.Footer>
				<Button type="button" variant="outline" onclick={() => (saveOpen = false)}>Cancel</Button>
				<Button type="submit" disabled={!canSave}>Save</Button>
			</Dialog.Footer>
		</form>
	</Dialog.Content>
</Dialog.Root>
