<script lang="ts">
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Pencil from '@lucide/svelte/icons/pencil';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { toast } from 'svelte-sonner';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import Hint from '$lib/components/hint.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import NoteComposer from './note-composer.svelte';
	import TriageBadge from './triage-badge.svelte';
	import { canChangeNote, noteHref, noteSubject, scanLabel } from './subject';
	import { notes } from '$lib/stores/notes.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { formatDateTime, relativeTime } from '$lib/utilities/dates';
	import { NOTE_STATUS_LABELS, type Note } from '$lib/types/note';

	interface Props {
		note: Note | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		onChanged?: (note: Note | null) => void;
	}

	let { note, open, onOpenChange, onChanged }: Props = $props();

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let current = $state<Note | null>(null);
	let editing = $state(false);
	let busy = $state(false);
	let confirmDelete = $state(false);
	let contentEl = $state<HTMLElement | null>(null);
	let shownFor = '';

	$effect(() => {
		const next = note;
		if (!next) return;
		current = next;
		if (next.id !== shownFor) {
			shownFor = next.id;
			editing = false;
		}
	});

	let resolved = $derived(current?.status === 'resolved');
	let changeable = $derived(!!current && canChangeNote(current, auth.user));
	let subject = $derived(current ? noteSubject(current) : null);
	let openHref = $derived(current ? noteHref(current) : null);

	function changed(next: Note | null) {
		if (next) current = next;
		onChanged?.(next);
	}

	async function toggleStatus() {
		if (busy || !projectId || !current) return;
		busy = true;
		try {
			changed(
				await notes.update(projectId, current.id, { status: resolved ? 'open' : 'resolved' })
			);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Note not updated.');
		} finally {
			busy = false;
		}
	}

	async function remove() {
		if (busy || !projectId || !current) return;
		busy = true;
		try {
			await notes.remove(projectId, current);
			confirmDelete = false;
			changed(null);
			onOpenChange(false);
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

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content
		bind:ref={contentEl}
		side="right"
		tabindex={-1}
		class="flex w-full flex-col gap-0 p-0 outline-none sm:max-w-lg"
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			contentEl?.focus();
		}}
	>
		{#if current && subject}
			{@const n = current}
			{@const Icon = subject.icon}
			<Sheet.Header class="gap-2 border-b px-5 pt-5 pr-12 pb-3">
				<Sheet.Title class="text-base font-medium">Note</Sheet.Title>
				<div class="flex items-center gap-2">
					<Sheet.Description
						class="flex min-w-0 flex-1 flex-wrap items-center gap-x-1.5 gap-y-1 text-xs"
					>
						{#if n.author}
							<span class="font-medium text-foreground">{n.author}</span>
							{@render dot()}
						{/if}
						<Hint text={formatDateTime(n.created_at)}>
							{#snippet child(props)}
								<span {...props}>{relativeTime(n.created_at)}</span>
							{/snippet}
						</Hint>
						{@render dot()}
						<span>{NOTE_STATUS_LABELS[n.status] ?? n.status}</span>
						{#if n.triage_state}
							<TriageBadge state={n.triage_state} class="ml-1" />
						{/if}
					</Sheet.Description>
					<DropdownMenu.Root>
						<DropdownMenu.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="ghost"
									size="icon"
									class="size-7 shrink-0 text-muted-foreground"
									disabled={busy || editing}
								>
									<Ellipsis class="size-4" />
									<span class="sr-only">Note actions</span>
								</Button>
							{/snippet}
						</DropdownMenu.Trigger>
						<DropdownMenu.Content
							align="end"
							class="w-40"
							onCloseAutoFocus={(e) => {
								if (editing || confirmDelete) e.preventDefault();
							}}
						>
							{#if changeable}
								<DropdownMenu.Item onSelect={() => (editing = true)}>
									<Pencil /> Edit
								</DropdownMenu.Item>
							{/if}
							<DropdownMenu.Item onSelect={toggleStatus}>
								{#if resolved}
									<RotateCcw /> Reopen
								{:else}
									<CircleCheck /> Resolve
								{/if}
							</DropdownMenu.Item>
							{#if changeable}
								<DropdownMenu.Separator />
								<DropdownMenu.Item variant="destructive" onSelect={() => (confirmDelete = true)}>
									<Trash2 /> Delete
								</DropdownMenu.Item>
							{/if}
						</DropdownMenu.Content>
					</DropdownMenu.Root>
				</div>
			</Sheet.Header>

			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col gap-6 px-5 py-4">
					{#if editing}
						<NoteComposer
							anchor={{
								targetId: n.target_id,
								scanId: n.scan_id,
								dimension: n.dimension,
								assetKey: n.asset_key,
								assetLabel: n.asset_label
							}}
							note={n}
							autofocus
							onSaved={(saved) => {
								editing = false;
								changed(saved);
							}}
							onCancel={() => (editing = false)}
						/>
					{:else}
						<div class="flex flex-col gap-2">
							{#if n.tags.length}
								<div class="flex flex-wrap gap-1">
									{#each n.tags as tag (tag)}
										<span
											class="rounded-sm bg-muted px-1.5 font-mono text-2xs leading-5 text-muted-foreground"
										>
											#{tag}
										</span>
									{/each}
								</div>
							{/if}
							{#if n.title}
								<h3 class="text-sm font-semibold wrap-anywhere">{n.title}</h3>
							{/if}
							<p class="text-sm whitespace-pre-wrap text-foreground/90 wrap-anywhere">{n.body}</p>
						</div>
					{/if}

					<section class="flex flex-col gap-2.5">
						<SectionHead title="Linked to" />
						<div class="flex items-start gap-2">
							<span class="flex h-5 shrink-0 items-center text-muted-foreground">
								<Icon class="size-3.5" />
							</span>
							<p class="min-w-0 flex-1 text-sm leading-5">
								<span class="font-mono wrap-anywhere">{subject.label}</span>
								<span class="text-muted-foreground"> · {subject.type}</span>
							</p>
							{#if openHref}
								<Button
									variant="outline"
									size="sm"
									class="h-7 shrink-0 gap-1 px-2 text-xs"
									href={openHref}
								>
									Open <ArrowRight class="size-3.5" />
								</Button>
							{/if}
						</div>
						{#if n.dimension}
							<p class="flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
								<span>Target</span>
								<a
									href={ROUTES.target(n.target_id)}
									class="font-mono text-foreground hover:text-primary">{n.target_value}</a
								>
								{#if n.scan_id}
									{@render dot()}
									<a href={ROUTES.scan(n.scan_id)} class="text-foreground hover:text-primary"
										>{scanLabel(n.scan_at)}</a
									>
								{/if}
							</p>
						{/if}
					</section>
				</div>
			</ScrollArea>
		{/if}
	</Sheet.Content>
</Sheet.Root>

<ConfirmDialog
	open={confirmDelete}
	title="Delete note"
	description={current?.title ? `Note ${current.title} is removed.` : 'The note is removed.'}
	confirmLabel="Delete"
	destructive
	loading={busy}
	loadingLabel="Deleting"
	onOpenChange={(o) => (confirmDelete = o)}
	onConfirm={remove}
/>
