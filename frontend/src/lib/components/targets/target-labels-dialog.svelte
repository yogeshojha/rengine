<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { toast } from 'svelte-sonner';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { TAG_COLORS } from '$lib/config/tags';
	import { targetsStore } from '$lib/stores/targets.svelte';

	type LabelKind = 'tag' | 'organization';

	interface Props {
		kind: LabelKind;
		open: boolean;
		onOpenChange: (open: boolean) => void;
	}

	let { kind, open, onOpenChange }: Props = $props();

	const NOUN: Record<LabelKind, string> = { tag: 'Tag', organization: 'Organization' };
	const PLURAL: Record<LabelKind, string> = { tag: 'Tags', organization: 'Organizations' };

	interface Row {
		id: string;
		name: string;
		color?: string;
		count: number;
	}

	let rows = $derived<Row[]>(
		kind === 'tag'
			? targetsStore.tags.map((t) => ({
					id: t.id,
					name: t.name,
					color: t.color,
					count: t.target_count ?? 0
				}))
			: targetsStore.organizations.map((o) => ({
					id: o.id,
					name: o.name,
					count: o.target_count ?? 0
				}))
	);

	let editing = $state<string | null>(null);
	let draftName = $state('');
	let draftColor = $state('');
	let saving = $state(false);
	let pendingDelete = $state<Row | null>(null);
	let deleting = $state(false);

	const sameColor = (a: string, b: string) => a.toLowerCase() === b.toLowerCase();
	const targetsLabel = (n: number) => `${n.toLocaleString()} ${n === 1 ? 'target' : 'targets'}`;

	let deleteDescription = $derived(
		pendingDelete
			? pendingDelete.count > 0
				? `${NOUN[kind]} ${pendingDelete.name} is removed from ${targetsLabel(pendingDelete.count)}.`
				: `${NOUN[kind]} ${pendingDelete.name} is removed.`
			: ''
	);

	$effect(() => {
		if (!open) editing = null;
	});

	function startEdit(row: Row) {
		editing = row.id;
		draftName = row.name;
		draftColor = row.color ?? '';
	}

	async function save(row: Row) {
		const name = draftName.trim();
		if (!name) return;
		saving = true;
		try {
			if (kind === 'tag') {
				await targetsStore.updateTag(row.id, { name, color: draftColor || undefined });
			} else {
				await targetsStore.updateOrganization(row.id, { name });
			}
			toast.success(`${NOUN[kind]} updated`);
			editing = null;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : `${NOUN[kind]} not updated`);
		} finally {
			saving = false;
		}
	}

	async function confirmDelete() {
		const row = pendingDelete;
		if (!row) return;
		deleting = true;
		try {
			if (kind === 'tag') await targetsStore.deleteTag(row.id);
			else await targetsStore.deleteOrganization(row.id);
			toast.success(`${NOUN[kind]} deleted`);
			pendingDelete = null;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : `${NOUN[kind]} not deleted`);
		} finally {
			deleting = false;
		}
	}
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>{PLURAL[kind]}</Dialog.Title>
		</Dialog.Header>
		{#if rows.length === 0}
			<EmptyState compact title="No {PLURAL[kind].toLowerCase()}" />
		{:else}
			<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-[60vh]">
				<ul class="divide-y">
					{#each rows as row (row.id)}
						<li class="py-2">
							{#if editing === row.id}
								<form
									class="flex items-center gap-2"
									onsubmit={(e) => {
										e.preventDefault();
										void save(row);
									}}
								>
									<Input
										bind:value={draftName}
										aria-label="{NOUN[kind]} name"
										class="h-8"
										onkeydown={(e) => {
											if (e.key === 'Escape') {
												e.stopPropagation();
												editing = null;
											}
										}}
									/>
									<LoadingButton
										type="submit"
										size="sm"
										loading={saving}
										disabled={!draftName.trim()}
									>
										Save
									</LoadingButton>
									<Button type="button" size="sm" variant="ghost" onclick={() => (editing = null)}>
										Cancel
									</Button>
								</form>
								{#if kind === 'tag'}
									<div class="mt-2 flex flex-wrap gap-1.5" role="radiogroup" aria-label="Colour">
										{#each TAG_COLORS as color (color)}
											{@const picked = sameColor(draftColor, color)}
											<button
												type="button"
												role="radio"
												aria-checked={picked}
												aria-label={color}
												class="flex size-6 items-center justify-center rounded-full border-2 {picked
													? 'border-foreground'
													: 'border-transparent'}"
												style="background-color: {color}"
												onclick={() => (draftColor = color)}
											>
												{#if picked}
													<Check class="size-3 text-white" />
												{/if}
											</button>
										{/each}
									</div>
								{/if}
							{:else}
								<div class="flex items-center gap-2">
									{#if row.color}
										<span class="flex h-5 items-center">
											<span
												class="size-2.5 shrink-0 rounded-full"
												style="background-color: {row.color}"
											></span>
										</span>
									{/if}
									<span class="min-w-0 flex-1 truncate text-sm">{row.name}</span>
									<span class="shrink-0 text-xs text-muted-foreground tabular-nums">
										{targetsLabel(row.count)}
									</span>
									<Hint text="Edit">
										{#snippet child(props)}
											<Button
												{...props}
												variant="ghost"
												size="icon"
												class="size-7"
												aria-label="Edit {row.name}"
												onclick={() => startEdit(row)}
											>
												<Pencil class="size-3.5" />
											</Button>
										{/snippet}
									</Hint>
									<Hint text="Delete">
										{#snippet child(props)}
											<Button
												{...props}
												variant="ghost"
												size="icon"
												class="size-7 text-muted-foreground hover:text-destructive"
												aria-label="Delete {row.name}"
												onclick={() => (pendingDelete = row)}
											>
												<Trash2 class="size-3.5" />
											</Button>
										{/snippet}
									</Hint>
								</div>
							{/if}
						</li>
					{/each}
				</ul>
			</ScrollArea>
		{/if}
	</Dialog.Content>
</Dialog.Root>

<ConfirmDialog
	open={pendingDelete !== null}
	title="Delete {NOUN[kind].toLowerCase()}"
	description={deleteDescription}
	confirmLabel="Delete"
	destructive
	loading={deleting}
	onOpenChange={(o) => {
		if (!o) pendingDelete = null;
	}}
	onConfirm={() => void confirmDelete()}
/>
