<script lang="ts">
	import { tick, untrack } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Textarea } from '$lib/components/ui/textarea';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import NoteTagInput from './note-tag-input.svelte';
	import { notes } from '$lib/stores/notes.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import type { Note, NoteAnchor } from '$lib/types/note';

	interface Props {
		anchor: NoteAnchor;
		note?: Note | null;
		initialBody?: string;
		autofocus?: boolean;
		onSaved?: (note: Note) => void;
		onCancel?: () => void;
	}

	let {
		anchor,
		note = null,
		initialBody = '',
		autofocus = false,
		onSaved,
		onCancel
	}: Props = $props();

	let projectId = $derived(projectsStore.activeProject?.id ?? '');

	const editing = untrack(() => note);
	const start = {
		body: editing?.body ?? untrack(() => initialBody),
		title: editing?.title ?? '',
		tags: editing ? [...editing.tags] : []
	};
	let body = $state(start.body);
	let title = $state(start.title);
	let tags = $state<string[]>([...start.tags]);
	let saving = $state(false);
	let failed = $state('');
	let tagError = $state<string | null>(null);
	let area = $state<HTMLTextAreaElement | null>(null);
	let tagInput = $state<ReturnType<typeof NoteTagInput> | null>(null);

	$effect(() => {
		if (autofocus) area?.focus();
	});

	let ready = $derived(body.trim().length > 0);

	async function save() {
		if (!ready || saving || !projectId) return;
		if (tagInput && !tagInput.commit()) return;
		saving = true;
		failed = '';
		try {
			const saved = editing
				? await notes.update(projectId, editing.id, {
						...(editing.title ? { title: title.trim() } : {}),
						body: body.trim(),
						tags
					})
				: await notes.create(projectId, {
						target_id: anchor.targetId,
						scan_id: anchor.scanId ?? null,
						dimension: anchor.dimension ?? null,
						asset_key: anchor.assetKey ?? null,
						asset_label: anchor.assetLabel ?? anchor.assetKey ?? null,
						body: body.trim(),
						tags
					});
			if (!editing) {
				body = '';
				tags = [];
			}
			onSaved?.(saved);
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Note not saved.';
		} finally {
			saving = false;
		}
		await tick();
		if (area?.isConnected) area.focus();
	}

	export function focus() {
		area?.focus();
	}

	export function dirty(): boolean {
		return (
			body.trim() !== start.body.trim() ||
			title.trim() !== start.title.trim() ||
			tags.join('\n') !== start.tags.join('\n') ||
			(tagInput?.draft() ?? '').trim() !== ''
		);
	}

	const guard = new DiscardGuard(dirty, () => onCancel?.());

	function onKey(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
			e.preventDefault();
			void save();
		} else if (e.key === 'Escape' && editing && onCancel) {
			e.preventDefault();
			e.stopPropagation();
			if (!saving) guard.close();
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="flex flex-col gap-2" onkeydown={onKey}>
	{#if editing?.title}
		<Input
			bind:value={title}
			placeholder="Title"
			aria-label="Title"
			class="h-8 text-sm font-semibold"
			disabled={saving}
		/>
	{/if}
	<Textarea
		bind:ref={area}
		bind:value={body}
		placeholder="Write a note"
		aria-label="Note"
		class="max-h-64 min-h-16 resize-none text-sm"
		disabled={saving}
		oninput={() => (failed = '')}
	/>
	<div class="flex items-start gap-2">
		<NoteTagInput
			bind:this={tagInput}
			bind:tags
			disabled={saving}
			onError={(message) => (tagError = message)}
			class="min-w-0 flex-1"
		/>
		<div class="flex shrink-0 items-center gap-1">
			{#if onCancel}
				<Button
					variant="ghost"
					size="sm"
					class="h-7 px-2 text-muted-foreground"
					onclick={() => guard.close()}
					disabled={saving}
				>
					Cancel
				</Button>
			{/if}
			<LoadingButton
				size="sm"
				class="h-7 px-3"
				loading={saving}
				disabled={!ready}
				loadingLabel="Saving"
				onclick={save}
			>
				{editing ? 'Save' : 'Add note'}
			</LoadingButton>
		</div>
	</div>
	{#if tagError || failed}
		<p role="alert" class="text-xs text-destructive">{tagError ?? failed}</p>
	{/if}
</div>

{#if onCancel}
	<UnsavedChangesDialog
		open={guard.asking}
		onOpenChange={(next) => (guard.asking = next)}
		onConfirm={guard.discard}
	/>
{/if}
