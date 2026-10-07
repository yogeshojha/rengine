<script lang="ts">
	import { Checkbox } from '$lib/components/ui/checkbox';
	import Hint from '$lib/components/hint.svelte';
	import TriageBadge from './triage-badge.svelte';
	import { noteSubject } from './subject';
	import { formatDateTime, relativeTime } from '$lib/utilities/dates';
	import { cn } from '$lib/utils';
	import type { Note } from '$lib/types/note';

	interface Props {
		note: Note;
		checked?: boolean;
		selectable?: boolean;
		active?: boolean;
		onCheck?: (id: string) => void;
		onOpen: (note: Note) => void;
	}

	let {
		note,
		checked = false,
		selectable = true,
		active = false,
		onCheck,
		onOpen
	}: Props = $props();

	const SHOWN_TAGS = 3;

	let subject = $derived(noteSubject(note));
	let resolved = $derived(note.status === 'resolved');
	let shownTags = $derived(note.tags.slice(0, SHOWN_TAGS));
	let moreTags = $derived(note.tags.slice(SHOWN_TAGS));
</script>

<div
	class={cn(
		'flex items-start gap-3 border-b px-4 transition-colors last:border-b-0 hover:bg-muted/40',
		active && 'bg-muted/40'
	)}
>
	{#if onCheck && selectable}
		<div class="flex h-11 shrink-0 items-center">
			<Checkbox {checked} onCheckedChange={() => onCheck(note.id)} aria-label="Select note" />
		</div>
	{:else if onCheck}
		<span class="w-4 shrink-0"></span>
	{/if}
	<button
		type="button"
		class={cn(
			'flex min-w-0 flex-1 flex-col gap-1 rounded-sm py-3 text-left focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none focus-visible:ring-inset',
			resolved && 'opacity-60'
		)}
		aria-current={active ? 'true' : undefined}
		onclick={() => onOpen(note)}
	>
		<span class="flex w-full items-start gap-3">
			<span class="flex min-w-0 flex-1 flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs">
				<span class="flex h-5 items-center text-muted-foreground">
					<subject.icon class="size-3.5" />
				</span>
				<span class="min-w-0 font-mono text-foreground wrap-anywhere">{subject.label}</span>
				<span class="text-muted-foreground/60" aria-hidden="true">·</span>
				<span class="text-muted-foreground">{subject.type}</span>
				{#if note.triage_state}
					<TriageBadge state={note.triage_state} class="ml-1" />
				{/if}
			</span>
			<span class="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
				{#if note.tags.length}
					<span class="hidden min-w-0 items-center gap-1 sm:flex">
						{#each shownTags as tag (tag)}
							<span
								class="max-w-32 truncate rounded-sm bg-muted px-1.5 font-mono text-2xs leading-5"
								title="#{tag}">#{tag}</span
							>
						{/each}
						{#if moreTags.length}
							<Hint text={moreTags.map((t) => `#${t}`).join(' ')}>
								{#snippet child(props)}
									<span
										{...props}
										class="rounded-sm bg-muted px-1.5 font-mono text-2xs leading-5 tabular-nums"
										>+{moreTags.length}</span
									>
								{/snippet}
							</Hint>
						{/if}
					</span>
				{/if}
				<span class="whitespace-nowrap">
					{#if note.author}<span class="text-foreground">{note.author}</span> ·{/if}
					<Hint text={formatDateTime(note.created_at)}>
						{#snippet child(props)}
							<span {...props}>{relativeTime(note.created_at)}</span>
						{/snippet}
					</Hint>
				</span>
			</span>
		</span>
		{#if note.title}
			<span class="line-clamp-1 max-w-[100ch] text-sm font-medium wrap-anywhere">{note.title}</span>
		{/if}
		<span
			class="line-clamp-2 max-w-[100ch] text-sm whitespace-pre-line text-foreground/90 wrap-anywhere"
			>{note.body}</span
		>
	</button>
</div>
