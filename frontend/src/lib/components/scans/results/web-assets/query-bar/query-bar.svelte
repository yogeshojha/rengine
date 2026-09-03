<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import CircleQuestionMark from '@lucide/svelte/icons/circle-question-mark';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Popover from '$lib/components/ui/popover';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
	import { Spinner } from '$lib/components/ui/spinner';
	import { querySchema } from '$lib/stores/query-schema.svelte';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { caretContext, lex, replaceRange, type QueryProblem } from '$lib/utilities/query-lexer';
	import type { QueryError } from '$lib/types/asset-query';
	import type { Facet } from '$lib/utilities/scan-insights';
	import QueryHighlight from './query-highlight.svelte';
	import QuerySuggestions from './query-suggestions.svelte';
	import QueryHelp from './query-help.svelte';
	import { buildSuggestions, type Suggestion } from './suggest';

	interface Props {
		value: string;
		facets: Record<string, Facet[]>;
		onChange: (value: string) => void;
		placeholder?: string;
		busy?: boolean;
		serverError?: QueryError | null;
		onReady?: (ready: boolean) => void;
		ref?: HTMLInputElement | null;
	}

	let {
		value,
		facets,
		onChange,
		placeholder = 'Search everything, or filter with status:>=500 tech:nginx is:live',
		busy = false,
		serverError = null,
		onReady,
		ref = $bindable(null)
	}: Props = $props();

	const RECENT_LIMIT = 6;
	const EXAMPLE_LIMIT = 4;

	let focused = $state(false);
	let dismissed = $state(false);
	let helpOpen = $state(false);
	let active = $state(0);
	let caret = $state(0);
	let anchor = $state<HTMLElement | null>(null);
	let overlay = $state<HTMLElement | null>(null);
	let recents = $state<string[]>(readRecents());

	$effect(() => {
		void querySchema.load();
	});

	let known = $derived((name: string) => querySchema.byName.has(name));
	let lexed = $derived(lex(value, known));
	let problems = $derived.by<QueryProblem[]>(() => {
		if (!serverError) return lexed.problems;
		if (lexed.problems.some((p) => p.level === 'error')) return lexed.problems;
		return [
			...lexed.problems,
			{
				start: serverError.start,
				end: Math.max(serverError.end, serverError.start + 1),
				message: serverError.message,
				level: 'error' as const
			}
		];
	});
	let notice = $derived(
		problems.find((p) => p.level === 'error') ?? problems.find((p) => p.level === 'warning') ?? null
	);
	let noticeHint = $derived(notice?.level === 'error' ? (serverError?.hint ?? null) : null);
	let ready = $derived(!lexed.incomplete && !lexed.problems.some((p) => p.level === 'error'));

	$effect(() => onReady?.(ready));

	let context = $derived(focused ? caretContext(value, caret, known) : null);
	let suggestions = $derived(
		buildSuggestions(context, querySchema.schema, facets, querySchema.byName)
	);
	let showStarters = $derived(
		!value.trim() && (recents.length > 0 || querySchema.schema.examples.length > 0)
	);
	let open = $derived(focused && !dismissed && (showStarters || suggestions.length > 0));

	$effect(() => {
		void suggestions;
		active = 0;
	});

	function readRecents(): string[] {
		try {
			const raw = localStorage.getItem(STORAGE_KEYS.webAssetsRecentQueries);
			const parsed = raw ? (JSON.parse(raw) as unknown) : [];
			return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === 'string') : [];
		} catch {
			return [];
		}
	}

	function writeRecents(next: string[]) {
		recents = next;
		try {
			localStorage.setItem(STORAGE_KEYS.webAssetsRecentQueries, JSON.stringify(next));
		} catch {
			// recent searches are a convenience
		}
	}

	export function remember(query: string) {
		const trimmed = query.trim();
		if (!trimmed) return;
		writeRecents([trimmed, ...recents.filter((r) => r !== trimmed)].slice(0, RECENT_LIMIT));
	}

	function syncCaret() {
		caret = ref?.selectionStart ?? value.length;
		if (overlay && ref) overlay.scrollLeft = ref.scrollLeft;
	}

	function emit(next: string, caretAt: number) {
		onChange(next);
		dismissed = false;
		requestAnimationFrame(() => {
			ref?.focus();
			ref?.setSelectionRange(caretAt, caretAt);
			syncCaret();
		});
	}

	function pick(suggestion: Suggestion) {
		if (!context) return;
		const next = replaceRange(value, context.start, context.end, suggestion.insert);
		emit(next, context.start + suggestion.insert.length);
	}

	function setQuery(next: string) {
		emit(next, next.length);
	}

	function insertFragment(fragment: string) {
		const spaced = value && !value.endsWith(' ') ? `${value} ` : value;
		emit(spaced + fragment, spaced.length + fragment.length);
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			if (open) {
				event.preventDefault();
				dismissed = true;
			} else if (value) {
				onChange('');
			}
			return;
		}
		if (event.key === '?' && !value) {
			event.preventDefault();
			helpOpen = true;
			return;
		}
		if (!open || showStarters) {
			if (event.key === 'ArrowDown' && !open) dismissed = false;
			return;
		}
		if (event.key === 'ArrowDown') {
			event.preventDefault();
			active = (active + 1) % suggestions.length;
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			active = (active - 1 + suggestions.length) % suggestions.length;
		} else if (event.key === 'Tab' || (event.key === 'Enter' && suggestions[active])) {
			event.preventDefault();
			pick(suggestions[active]);
		}
	}
</script>

<div class="flex w-full flex-col gap-1.5">
	<div
		bind:this={anchor}
		class="flex h-12 w-full items-center gap-2 rounded-xl border border-input bg-background px-3 shadow-xs transition-[color,box-shadow] focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/50
			{notice?.level === 'error' ? 'border-destructive/60 focus-within:border-destructive' : ''}"
	>
		{#if busy}
			<Spinner class="size-4 shrink-0 text-muted-foreground" />
		{:else}
			<Search class="size-4 shrink-0 text-muted-foreground" />
		{/if}

		<div class="relative min-w-0 flex-1">
			<div
				bind:this={overlay}
				aria-hidden="true"
				class="pointer-events-none absolute inset-0 overflow-hidden font-mono text-sm leading-[1.5rem] whitespace-pre"
			>
				{#if value}
					<QueryHighlight source={value} tokens={lexed.tokens} {problems} />
				{:else}
					<span class="text-muted-foreground">{placeholder}</span>
				{/if}
			</div>
			<input
				bind:this={ref}
				{value}
				type="text"
				role="combobox"
				aria-expanded={open}
				aria-controls="query-suggestions"
				aria-activedescendant={open && !showStarters ? `query-option-${active}` : undefined}
				aria-label="Search web assets"
				autocomplete="off"
				autocapitalize="off"
				autocorrect="off"
				spellcheck={false}
				maxlength={querySchema.schema.max_length}
				class="relative w-full bg-transparent font-mono text-sm leading-[1.5rem] text-transparent caret-foreground outline-none selection:bg-primary/25"
				oninput={(e) => {
					dismissed = false;
					onChange(e.currentTarget.value);
					syncCaret();
				}}
				onkeydown={onKeydown}
				onkeyup={syncCaret}
				onclick={syncCaret}
				onscroll={syncCaret}
				onselect={syncCaret}
				onfocus={() => {
					focused = true;
					dismissed = false;
					syncCaret();
				}}
				onblur={() => (focused = false)}
			/>
		</div>

		{#if value}
			<Tooltip.Root>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-7 shrink-0 text-muted-foreground"
							aria-label="Clear search"
							onclick={() => setQuery('')}
						>
							<X class="size-4" />
						</Button>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Content>Clear <Kbd>Esc</Kbd></Tooltip.Content>
			</Tooltip.Root>
		{:else}
			<Kbd class="shrink-0 max-sm:hidden">/</Kbd>
		{/if}

		<Tooltip.Root>
			<Tooltip.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="size-7 shrink-0 text-muted-foreground"
						aria-label="Search syntax reference"
						onclick={() => (helpOpen = true)}
					>
						<CircleQuestionMark class="size-4" />
					</Button>
				{/snippet}
			</Tooltip.Trigger>
			<Tooltip.Content>What can I search?</Tooltip.Content>
		</Tooltip.Root>
	</div>

	{#if notice}
		<p
			class="flex items-start gap-1.5 px-1 text-xs {notice.level === 'error'
				? 'text-destructive'
				: 'text-warning'}"
		>
			<TriangleAlert class="mt-0.5 size-3.5 shrink-0" />
			<span>
				{notice.message}
				{#if noticeHint}<span class="text-muted-foreground">{noticeHint}</span>{/if}
			</span>
		</p>
	{/if}
</div>

<Popover.Root
	{open}
	onOpenChange={(next) => {
		if (!next) dismissed = true;
	}}
>
	<Popover.Content
		id="query-suggestions"
		customAnchor={anchor}
		align="start"
		sideOffset={6}
		trapFocus={false}
		onOpenAutoFocus={(e) => e.preventDefault()}
		onCloseAutoFocus={(e) => e.preventDefault()}
		onmousedown={(e: MouseEvent) => e.preventDefault()}
		class="w-(--bits-popover-anchor-width) overflow-hidden p-0"
	>
		<QuerySuggestions
			{suggestions}
			{active}
			{recents}
			examples={querySchema.schema.examples.slice(0, EXAMPLE_LIMIT)}
			{showStarters}
			onPick={pick}
			onQuery={setQuery}
			onForget={(query) => writeRecents(recents.filter((r) => r !== query))}
			onHover={(index) => (active = index)}
		/>
	</Popover.Content>
</Popover.Root>

<QueryHelp
	open={helpOpen}
	schema={querySchema.schema}
	onOpenChange={(next) => (helpOpen = next)}
	onInsert={insertFragment}
	onQuery={setQuery}
/>
