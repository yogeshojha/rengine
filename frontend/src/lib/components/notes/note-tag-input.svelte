<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';
	import * as Popover from '$lib/components/ui/popover';
	import { notes } from '$lib/stores/notes.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { MAX_NOTE_TAGS, type NoteTagCount } from '$lib/types/note';
	import { cn } from '$lib/utils';
	import { noteTag, noteTagError, splitNoteTags, TOO_MANY_TAGS } from './tags';

	interface Props {
		tags: string[];
		disabled?: boolean;
		onError?: (message: string | null) => void;
		class?: string;
	}

	let { tags = $bindable([]), disabled = false, onError, class: className }: Props = $props();

	const SUGGEST_DEBOUNCE_MS = 150;
	const SHOWN = 8;

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let text = $state('');
	let focused = $state(false);
	let dismissed = $state(false);
	let highlight = $state(-1);
	let found = $state<NoteTagCount[]>([]);
	let inputEl = $state<HTMLInputElement | null>(null);
	let boxEl = $state<HTMLDivElement | null>(null);
	let seq = 0;

	let typed = $derived(noteTag(text));
	let visible = $derived(
		found.filter((t) => t.name.startsWith(typed) && !tags.includes(t.name)).slice(0, SHOWN)
	);
	let open = $derived(focused && !dismissed && !disabled && visible.length > 0);
	let offerTyped = $derived(
		!!typed && !tags.includes(typed) && !visible.some((t) => t.name === typed)
	);

	$effect(() => {
		const q = typed;
		const id = projectId;
		if (!focused || !id) return;
		const mine = ++seq;
		const timer = setTimeout(async () => {
			try {
				const rows = await notes.tags(id, q);
				if (mine === seq) found = rows;
			} catch {
				if (mine === seq) found = [];
			}
		}, SUGGEST_DEBOUNCE_MS);
		return () => clearTimeout(timer);
	});

	$effect(() => {
		void visible;
		highlight = -1;
	});

	function accept(next: string[]): boolean {
		if (next.length > MAX_NOTE_TAGS) {
			onError?.(TOO_MANY_TAGS);
			return false;
		}
		tags = next;
		text = '';
		onError?.(null);
		return true;
	}

	function add(name: string) {
		accept(tags.includes(name) ? tags : [...tags, name]);
		inputEl?.focus();
	}

	/** Moves the typed text into chips and reports whether every tag was taken. */
	export function commit(): boolean {
		const parts = splitNoteTags(text);
		if (!parts.length) {
			text = '';
			return true;
		}
		const refused = parts.map(noteTagError).find(Boolean);
		if (refused) {
			onError?.(refused);
			return false;
		}
		return accept([...tags, ...parts.filter((p) => !tags.includes(p))]);
	}

	export function draft(): string {
		return text;
	}

	function remove(name: string) {
		tags = tags.filter((t) => t !== name);
		onError?.(null);
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			if (e.metaKey || e.ctrlKey || e.isComposing) return;
			e.preventDefault();
			if (open && highlight >= 0 && visible[highlight]) add(visible[highlight].name);
			else commit();
		} else if (e.key === ',') {
			e.preventDefault();
			commit();
		} else if (e.key === 'Tab' && !e.shiftKey && open && highlight >= 0 && visible[highlight]) {
			e.preventDefault();
			add(visible[highlight].name);
		} else if (e.key === 'ArrowDown' && visible.length) {
			e.preventDefault();
			dismissed = false;
			highlight = (highlight + 1) % visible.length;
		} else if (e.key === 'ArrowUp' && visible.length) {
			e.preventDefault();
			dismissed = false;
			highlight = highlight <= 0 ? visible.length - 1 : highlight - 1;
		} else if (e.key === 'Backspace' && !text && tags.length) {
			remove(tags[tags.length - 1]);
		} else if (e.key === 'Escape' && (open || text)) {
			e.preventDefault();
			e.stopPropagation();
			if (open) dismissed = true;
			else text = '';
		}
	}

	function onPaste(e: ClipboardEvent) {
		const pasted = e.clipboardData?.getData('text') ?? '';
		if (!/[,\n]/.test(pasted)) return;
		e.preventDefault();
		text = `${text}${pasted}`;
		commit();
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div
	bind:this={boxEl}
	class={cn(
		'flex min-h-7 cursor-text flex-wrap items-center gap-1 rounded-md px-1 py-0.5 transition-colors focus-within:bg-muted/50 hover:bg-muted/50',
		disabled && 'pointer-events-none opacity-50',
		className
	)}
	onclick={() => inputEl?.focus()}
>
	{#each tags as tag (tag)}
		<span
			class="inline-flex h-5 items-center gap-0.5 rounded-sm bg-muted pr-0.5 pl-1.5 font-mono text-xs text-secondary-foreground"
		>
			#{tag}
			<button
				type="button"
				class="rounded-sm p-0.5 text-muted-foreground hover:bg-foreground/10 hover:text-foreground"
				aria-label="Remove tag {tag}"
				{disabled}
				onclick={(e) => {
					e.stopPropagation();
					remove(tag);
					inputEl?.focus();
				}}
			>
				<X class="size-3" />
			</button>
		</span>
	{/each}
	<input
		bind:this={inputEl}
		bind:value={text}
		class="h-6 min-w-24 flex-1 bg-transparent px-1 text-xs outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
		placeholder="Add tag"
		aria-label="Add tag"
		autocomplete="off"
		spellcheck="false"
		{disabled}
		onkeydown={onKeydown}
		onpaste={onPaste}
		oninput={() => {
			dismissed = false;
			onError?.(null);
		}}
		onfocus={() => {
			focused = true;
			dismissed = false;
		}}
		onblur={() => (focused = false)}
	/>
</div>

<Popover.Root
	{open}
	onOpenChange={(next) => {
		if (!next) dismissed = true;
	}}
>
	<Popover.Content
		customAnchor={boxEl}
		align="start"
		sideOffset={4}
		trapFocus={false}
		onOpenAutoFocus={(e) => e.preventDefault()}
		onCloseAutoFocus={(e) => e.preventDefault()}
		onInteractOutside={(e) => {
			if (e.target instanceof Node && boxEl?.contains(e.target)) e.preventDefault();
		}}
		onmousedown={(e: MouseEvent) => e.preventDefault()}
		class="w-64 p-1"
	>
		<ul role="listbox" aria-label="Note tags">
			{#each visible as tag, i (tag.name)}
				<li>
					<button
						type="button"
						role="option"
						aria-selected={i === highlight}
						class="flex h-8 w-full items-center gap-2 rounded-sm px-2 text-left {i === highlight
							? 'bg-accent'
							: ''}"
						onpointermove={() => (highlight = i)}
						onclick={() => add(tag.name)}
					>
						<span class="min-w-0 flex-1 truncate font-mono text-xs">#{tag.name}</span>
						<span class="text-2xs text-muted-foreground tabular-nums">
							{tag.count.toLocaleString()}
						</span>
					</button>
				</li>
			{/each}
			{#if offerTyped}
				<li>
					<button
						type="button"
						class="flex h-8 w-full items-center gap-2 rounded-sm px-2 text-left text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
						onpointermove={() => (highlight = -1)}
						onclick={() => {
							commit();
							inputEl?.focus();
						}}
					>
						<Plus class="size-3.5 shrink-0" />
						<span class="truncate">Add <span class="font-mono">#{typed}</span></span>
					</button>
				</li>
			{/if}
		</ul>
	</Popover.Content>
</Popover.Root>
