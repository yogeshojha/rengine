<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Dialog from '$lib/components/ui/dialog';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import { Input } from '$lib/components/ui/input';
	import FormField from '$lib/components/form-field.svelte';
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

	const KEY = STORAGE_KEYS.targetViews;

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
			<Button {...props} variant="outline" aria-label="Views">
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
				<DropdownMenu.Item
					onSelect={() => onApply(view.query)}
					aria-current={active ? 'true' : undefined}
				>
					<Check class={active ? 'opacity-100' : 'opacity-0'} />
					<span class="min-w-0 truncate {active ? 'font-medium' : ''}" title={view.name}
						>{view.name}</span
					>
				</DropdownMenu.Item>
			{/each}
			<DropdownMenu.Separator />
			<DropdownMenu.Sub>
				<DropdownMenu.SubTrigger class="gap-2">
					<Trash2 class="size-4 text-muted-foreground" />
					Delete a view
				</DropdownMenu.SubTrigger>
				<DropdownMenu.SubContent class="w-56">
					{#each views as view (view.name)}
						<DropdownMenu.Item
							variant="destructive"
							onSelect={() => (pendingDelete = view)}
							aria-label="Delete view {view.name}"
						>
							<span class="min-w-0 truncate" title={view.name}>{view.name}</span>
						</DropdownMenu.Item>
					{/each}
				</DropdownMenu.SubContent>
			</DropdownMenu.Sub>
		{/if}
	</DropdownMenu.Content>
</DropdownMenu.Root>

<ConfirmDialog
	open={!!pendingDelete}
	title="Delete view"
	description={`Saved view "${pendingDelete?.name ?? ''}" is removed.`}
	confirmLabel="Delete"
	destructive
	onOpenChange={(o) => {
		if (!o) pendingDelete = null;
	}}
	onConfirm={confirmDelete}
/>

<Dialog.Root bind:open={saveOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Save view</Dialog.Title>
		</Dialog.Header>
		<form onsubmit={confirmSave} class="flex flex-col gap-4">
			<FormField label="View name">
				{#snippet children({ id })}
					<Input {id} bind:value={newName} placeholder="Responding web assets" autofocus />
				{/snippet}
			</FormField>
			<Dialog.Footer>
				<Button type="button" variant="outline" onclick={() => (saveOpen = false)}>Cancel</Button>
				<Button type="submit" disabled={!canSave}>Save</Button>
			</Dialog.Footer>
		</form>
	</Dialog.Content>
</Dialog.Root>
