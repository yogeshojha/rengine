<script lang="ts">
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Pencil from '@lucide/svelte/icons/pencil';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import NoteComposer from './note-composer.svelte';
	import { notes } from '$lib/stores/notes.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { SURFACE_ORDER } from '$lib/config/surface';
	import { ROUTES } from '$lib/config/routes';
	import type { Note } from '$lib/types/note';

	interface Props {
		note: Note;
		showAnchor?: boolean;
		onChanged?: () => void;
	}

	let { note, showAnchor = true, onChanged }: Props = $props();

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let editing = $state(false);
	let busy = $state(false);
	let resolved = $derived(note.status === 'resolved');
	let spec = $derived(SURFACE_ORDER.find((s) => s.key === note.dimension) ?? null);

	async function toggleStatus() {
		if (busy || !projectId) return;
		busy = true;
		try {
			await notes.update(projectId, note.id, { status: resolved ? 'open' : 'resolved' });
			onChanged?.();
		} finally {
			busy = false;
		}
	}

	async function remove() {
		if (busy || !projectId) return;
		busy = true;
		try {
			await notes.remove(projectId, note);
			onChanged?.();
		} finally {
			busy = false;
		}
	}
</script>

<article
	class="flex flex-col gap-2 border-b px-4 py-3 last:border-b-0 {resolved ? 'opacity-60' : ''}"
>
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
		<div class="flex items-start gap-2">
			<div class="flex min-w-0 flex-1 flex-col gap-1">
				{#if note.title}
					<h4 class="text-sm font-semibold {resolved ? 'line-through' : ''}">{note.title}</h4>
				{/if}
				<p class="text-sm whitespace-pre-wrap text-foreground/90">{note.body}</p>
			</div>
			<div class="flex shrink-0 items-center gap-0.5">
				<Hint text={resolved ? 'Reopen' : 'Resolve'}>
					{#snippet child(props)}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-7 text-muted-foreground"
							onclick={toggleStatus}
							disabled={busy}
						>
							{#if resolved}
								<RotateCcw class="size-3.5" />
							{:else}
								<CircleCheck class="size-3.5" />
							{/if}
						</Button>
					{/snippet}
				</Hint>
				<Hint text="Edit">
					{#snippet child(props)}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-7 text-muted-foreground"
							onclick={() => (editing = true)}
							disabled={busy}
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
							onclick={remove}
							disabled={busy}
						>
							<Trash2 class="size-3.5" />
						</Button>
					{/snippet}
				</Hint>
			</div>
		</div>

		<div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
			{#each note.tags as tag (tag.id)}
				<Badge variant="outline" class="gap-1 bg-background font-normal">
					<span class="size-2 shrink-0 rounded-full" style="background-color: {tag.color}"></span>
					{tag.name}
				</Badge>
			{/each}
			{#if showAnchor && note.asset_label}
				<span class="font-mono">{note.asset_label}</span>
				{#if spec}
					<span class="text-muted-foreground/60">·</span>
					<span>{spec.noun}</span>
				{/if}
			{/if}
			{#if showAnchor}
				<span class="text-muted-foreground/60">·</span>
				<a href={ROUTES.target(note.target_id)} class="hover:text-foreground hover:underline">
					{note.target_value}
				</a>
			{/if}
			<span class="text-muted-foreground/60">·</span>
			<span>{relativeTime(note.created_at)}</span>
			{#if note.author}
				<span class="text-muted-foreground/60">·</span>
				<span>{note.author}</span>
			{/if}
			{#if resolved}
				<Badge variant="outline" class="font-normal">Resolved</Badge>
			{/if}
		</div>
	{/if}
</article>
