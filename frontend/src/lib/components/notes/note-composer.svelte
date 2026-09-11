<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Textarea } from '$lib/components/ui/textarea';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { notes } from '$lib/stores/notes.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import type { Note, NoteAnchor } from '$lib/types/note';

	interface Props {
		anchor: NoteAnchor;
		note?: Note | null;
		autofocus?: boolean;
		onSaved?: (note: Note) => void;
		onCancel?: () => void;
	}

	let { anchor, note = null, autofocus = false, onSaved, onCancel }: Props = $props();

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let projectSlug = $derived(projectsStore.activeProject?.slug ?? '');

	const editing = untrack(() => note);
	let body = $state(editing?.body ?? '');
	let title = $state(editing?.title ?? '');
	let picked = new SvelteSet<string>(editing?.tags.map((t) => t.id) ?? []);
	let saving = $state(false);
	let failed = $state('');
	let area = $state<HTMLTextAreaElement | null>(null);

	const TAG_SCROLL_AT = 12;

	$effect(() => {
		if (projectSlug && projectId) void notes.loadTags(projectSlug, projectId);
	});

	$effect(() => {
		if (autofocus) area?.focus();
	});

	let ready = $derived(body.trim().length > 0 && picked.size > 0);

	function toggle(id: string) {
		if (picked.has(id)) picked.delete(id);
		else picked.add(id);
	}

	async function save() {
		if (!ready || saving || !projectId) return;
		saving = true;
		failed = '';
		try {
			const saved = note
				? await notes.update(projectId, note.id, {
						title: title.trim() || null,
						body: body.trim(),
						tag_ids: [...picked]
					})
				: await notes.create(projectId, {
						target_id: anchor.targetId,
						scan_id: anchor.scanId ?? null,
						dimension: anchor.dimension ?? null,
						asset_key: anchor.assetKey ?? null,
						asset_label: anchor.assetLabel ?? anchor.assetKey ?? null,
						title: title.trim() || null,
						body: body.trim(),
						tag_ids: [...picked]
					});
			body = note ? body : '';
			title = note ? title : '';
			if (!note) picked.clear();
			onSaved?.(saved);
		} catch (e) {
			failed = e instanceof Error ? e.message : 'The note could not be saved';
		} finally {
			saving = false;
		}
	}

	function onKey(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
			e.preventDefault();
			void save();
		}
	}
</script>

{#snippet tagList()}
	<div class="flex flex-wrap gap-1.5">
		{#each notes.tags as tag (tag.id)}
			<button
				type="button"
				class="inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs transition-colors {picked.has(
					tag.id
				)
					? 'border-primary/40 bg-primary/10 text-foreground'
					: 'bg-background text-muted-foreground hover:text-foreground'}"
				onclick={() => toggle(tag.id)}
				disabled={saving}
				aria-pressed={picked.has(tag.id)}
			>
				{#if picked.has(tag.id)}
					<Check class="size-3" />
				{:else}
					<span class="size-2 shrink-0 rounded-full" style="background-color: {tag.color}"></span>
				{/if}
				{tag.name}
			</button>
		{/each}
	</div>
{/snippet}

<div class="flex flex-col gap-2.5">
	<Textarea
		bind:ref={area}
		bind:value={body}
		onkeydown={onKey}
		rows={3}
		placeholder="Write what you found"
		class="resize-y text-sm"
		disabled={saving}
	/>

	{#if body.trim()}
		<Input
			bind:value={title}
			placeholder="Title (optional)"
			class="h-8 text-sm"
			disabled={saving}
		/>
	{/if}

	<div class="flex flex-col gap-1.5">
		<span class="text-xs text-muted-foreground">Tags</span>
		{#if notes.tags.length === 0}
			<span class="text-xs text-muted-foreground">
				No tags in this project yet. Add one in Settings to save a note.
			</span>
		{:else if notes.tags.length > TAG_SCROLL_AT}
			<ScrollArea class="h-[76px]">
				{@render tagList()}
			</ScrollArea>
		{:else}
			{@render tagList()}
		{/if}
	</div>

	{#if failed}
		<p class="text-xs text-destructive">{failed}</p>
	{/if}

	<div class="flex items-center gap-2">
		<LoadingButton
			size="sm"
			class="h-7 px-3"
			loading={saving}
			disabled={!ready}
			loadingLabel="Saving…"
			onclick={save}
		>
			{note ? 'Save' : 'Add note'}
		</LoadingButton>
		{#if onCancel}
			<Button
				variant="ghost"
				size="sm"
				class="h-7 px-2 text-muted-foreground"
				onclick={onCancel}
				disabled={saving}
			>
				Cancel
			</Button>
		{/if}
		{#if !ready && body.trim() && picked.size === 0 && notes.tags.length > 0}
			<span class="text-xs text-muted-foreground">Pick at least one tag</span>
		{/if}
	</div>
</div>
