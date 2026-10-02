<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Pencil from '@lucide/svelte/icons/pencil';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import Hint from '$lib/components/hint.svelte';
	import NoteComposer from './note-composer.svelte';
	import TriageBadge from './triage-badge.svelte';
	import { holdSheetKeys } from './keys';
	import { notes } from '$lib/stores/notes.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { formatDateTime, relativeTime } from '$lib/utilities/dates';
	import { SURFACE_ORDER } from '$lib/config/surface';
	import { ROUTES } from '$lib/config/routes';
	import { cn } from '$lib/utils';
	import type { Note } from '$lib/types/note';

	interface Props {
		note: Note;
		showAnchor?: boolean;
		checked?: boolean;
		onCheck?: (id: string) => void;
		onChanged?: () => void;
		class?: string;
	}

	let {
		note,
		showAnchor = true,
		checked = false,
		onCheck,
		onChanged,
		class: className
	}: Props = $props();

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let editing = $state(false);
	let busy = $state(false);
	let confirmDelete = $state(false);
	let resolved = $derived(note.status === 'resolved');
	let spec = $derived(SURFACE_ORDER.find((s) => s.key === note.dimension) ?? null);
	let bodyEl = $state<HTMLParagraphElement | null>(null);
	let expanded = $state(false);
	let clamped = $state(false);

	$effect(() => {
		void note.body;
		expanded = false;
	});

	$effect(() => {
		const el = bodyEl;
		void note.body;
		if (!el || expanded) return;
		const measure = () => (clamped = el.scrollHeight > el.clientHeight + 1);
		measure();
		const ro = new ResizeObserver(measure);
		ro.observe(el);
		return () => ro.disconnect();
	});

	async function toggleStatus() {
		if (busy || !projectId) return;
		busy = true;
		try {
			await notes.update(projectId, note.id, { status: resolved ? 'open' : 'resolved' });
			onChanged?.();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Note not updated.');
		} finally {
			busy = false;
		}
	}

	async function remove() {
		if (busy || !projectId) return;
		busy = true;
		try {
			await notes.remove(projectId, note);
			confirmDelete = false;
			onChanged?.();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Note not deleted.');
		} finally {
			busy = false;
		}
	}
</script>

{#snippet dot()}
	<span class="text-muted-foreground/60" aria-hidden="true">·</span>
{/snippet}

<article class={cn('flex gap-3 py-3', resolved && !editing && 'opacity-60', className)}>
	{#if onCheck && !editing}
		<div class="flex h-7 shrink-0 items-center">
			<Checkbox {checked} onCheckedChange={() => onCheck(note.id)} aria-label="Select note" />
		</div>
	{/if}
	<div class="flex min-w-0 flex-1 flex-col gap-1">
		{#if editing}
			<NoteComposer
				anchor={{
					targetId: note.target_id,
					scanId: note.scan_id,
					dimension: note.dimension,
					assetKey: note.asset_key,
					assetLabel: note.asset_label
				}}
				{note}
				autofocus
				onSaved={() => {
					editing = false;
					onChanged?.();
				}}
				onCancel={() => (editing = false)}
			/>
		{:else}
			<div class="flex items-center gap-2">
				<div
					class="flex min-w-0 flex-1 flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs text-muted-foreground"
				>
					{#if note.author}
						<span class="font-medium text-foreground">{note.author}</span>
						{@render dot()}
					{/if}
					<Hint text={formatDateTime(note.created_at)}>
						{#snippet child(props)}
							<span {...props}>{relativeTime(note.created_at)}</span>
						{/snippet}
					</Hint>
					{#if showAnchor && note.asset_label}
						{@render dot()}
						<span class="min-w-0 font-mono wrap-anywhere">{note.asset_label}</span>
						{#if spec}
							{@render dot()}
							<span>{spec.noun}</span>
						{/if}
					{/if}
					{#if showAnchor}
						{@render dot()}
						<a href={ROUTES.target(note.target_id)} class="hover:text-foreground">
							{note.target_value}
						</a>
					{/if}
					{#if resolved}
						{@render dot()}
						<span>Resolved</span>
					{/if}
					{#if note.triage_state}
						<TriageBadge state={note.triage_state} />
					{/if}
				</div>
				{#if note.tags.length}
					<div class="flex max-w-[50%] flex-wrap justify-end gap-1">
						{#each note.tags as tag (tag)}
							<span
								class="rounded-sm bg-muted px-1.5 font-mono text-2xs leading-5 text-muted-foreground"
							>
								#{tag}
							</span>
						{/each}
					</div>
				{/if}
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon"
								class="size-7 shrink-0 text-muted-foreground"
								disabled={busy}
							>
								<Ellipsis class="size-4" />
								<span class="sr-only">Note actions</span>
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content
						align="end"
						class="w-40"
						onkeydown={holdSheetKeys}
						onCloseAutoFocus={(e) => {
							if (editing || confirmDelete) e.preventDefault();
						}}
					>
						<DropdownMenu.Item onSelect={() => (editing = true)}>
							<Pencil /> Edit
						</DropdownMenu.Item>
						<DropdownMenu.Item onSelect={toggleStatus}>
							{#if resolved}
								<RotateCcw /> Reopen
							{:else}
								<CircleCheck /> Resolve
							{/if}
						</DropdownMenu.Item>
						<DropdownMenu.Separator />
						<DropdownMenu.Item variant="destructive" onSelect={() => (confirmDelete = true)}>
							<Trash2 /> Delete
						</DropdownMenu.Item>
					</DropdownMenu.Content>
				</DropdownMenu.Root>
			</div>
			<div class="flex flex-col gap-0.5">
				{#if note.title}
					<h4 class="text-sm font-semibold wrap-anywhere">{note.title}</h4>
				{/if}
				<p
					bind:this={bodyEl}
					class="text-sm whitespace-pre-wrap text-foreground/90 wrap-anywhere {expanded
						? ''
						: 'line-clamp-4'}"
				>
					{note.body}
				</p>
				{#if clamped || expanded}
					<button
						type="button"
						class="w-fit rounded-sm text-xs text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
						aria-expanded={expanded}
						onclick={() => (expanded = !expanded)}
					>
						{expanded ? 'Show less' : 'Show more'}
					</button>
				{/if}
			</div>
		{/if}
	</div>
</article>

<ConfirmDialog
	open={confirmDelete}
	title="Delete note"
	description={note.title ? `Note ${note.title} is removed.` : 'The note is removed.'}
	confirmLabel="Delete"
	destructive
	loading={busy}
	loadingLabel="Deleting"
	onOpenChange={(o) => (confirmDelete = o)}
	onConfirm={remove}
/>
