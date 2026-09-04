<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import CircleQuestionMark from '@lucide/svelte/icons/circle-question-mark';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Popover from '$lib/components/ui/popover';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
	import { Separator } from '$lib/components/ui/separator';
	import { Spinner } from '$lib/components/ui/spinner';
	import type { QuerySchemaStore } from '$lib/stores/query-schema.svelte';
	import { caretContext, lex, replaceRange, type QueryProblem } from '$lib/utilities/query-lexer';
	import type { QueryError, QueryLeads, QueryStarter } from '$lib/types/asset-query';
	import type { Facet } from '$lib/utilities/scan-insights';
	import QueryHighlight from './query-highlight.svelte';
	import QuerySuggestions from './query-suggestions.svelte';
	import QueryHelp from './query-help.svelte';
	import FindingsDialog from './findings-dialog.svelte';
	import { buildSuggestions, type Suggestion } from './suggest';

	interface Props {
		store: QuerySchemaStore;
		recentsKey: string;
		hint: string;
		value: string;
		facets: Record<string, Facet[]>;
		onChange: (value: string) => void;
		busy?: boolean;
		leadSet?: QueryLeads | null;
		total?: number | null;
		capped?: boolean;
		serverError?: QueryError | null;
		onReady?: (ready: boolean) => void;
		onSubmit?: () => void;
		ref?: HTMLInputElement | null;
	}

	let {
		store,
		recentsKey,
		hint,
		value,
		facets,
		onChange,
		busy = false,
		leadSet = null,
		total = null,
		capped = false,
		serverError = null,
		onReady,
		onSubmit,
		ref = $bindable(null)
	}: Props = $props();

	const RECENT_LIMIT = 6;
	const EXAMPLE_LIMIT = 6;
	const TEXT = 'font-mono text-sm leading-6';

	let focused = $state(false);
	let dismissed = $state(false);
	let helpOpen = $state(false);
	let findingsOpen = $state(false);
	let active = $state(-1);
	let caret = $state(0);
	let anchor = $state<HTMLElement | null>(null);
	let overlay = $state<HTMLElement | null>(null);
	let recents = $state<string[]>(readRecents());
	let stuck = $state(false);

	$effect(() => {
		void store.load();
	});

	$effect(() => {
		const wrap = anchor?.parentElement;
		const root = anchor?.closest('[data-slot=scroll-area-viewport]');
		if (!wrap || !root) return;
		let frame = 0;
		const measure = () => {
			frame = 0;
			const style = getComputedStyle(wrap);
			if (style.position !== 'sticky') {
				stuck = false;
				return;
			}
			const offset = parseFloat(style.top) || 0;
			stuck = wrap.getBoundingClientRect().top - root.getBoundingClientRect().top <= offset + 0.5;
		};
		const schedule = () => {
			if (!frame) frame = requestAnimationFrame(measure);
		};
		measure();
		root.addEventListener('scroll', schedule, { passive: true });
		window.addEventListener('resize', schedule);
		return () => {
			root.removeEventListener('scroll', schedule);
			window.removeEventListener('resize', schedule);
			if (frame) cancelAnimationFrame(frame);
		};
	});

	let schema = $derived(store.schema);
	let noun = $derived(schema.noun);
	let nounPlural = $derived(schema.noun_plural);
	let known = $derived((name: string) => store.byName.has(name));
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
	let hasError = $derived(notice?.level === 'error');
	let countLabel = $derived.by(() => {
		if (!value.trim() || hasError || total == null || busy) return null;
		const n = capped ? `${total.toLocaleString()}+` : total.toLocaleString();
		return `${n} ${total === 1 && !capped ? noun : nounPlural}`;
	});

	$effect(() => onReady?.(ready));

	let context = $derived(focused ? caretContext(value, caret, known) : null);
	let suggestions = $derived(buildSuggestions(context, schema, facets, store.byName));
	let findings = $derived((leadSet?.leads ?? []).filter((lead) => lead.count > 0));
	let counted = $derived(findings.length > 0);
	let findingWord = $derived(findings.length === 1 ? 'finding' : 'findings');
	let starters = $derived.by<QueryStarter[]>(() => {
		if (counted) return findings;
		const generic = schema.examples.filter((example) => example.generic);
		return generic.length ? generic : schema.examples;
	});
	let showStarters = $derived(!value.trim() && (recents.length > 0 || starters.length > 0));
	let open = $derived(focused && !dismissed && (showStarters || suggestions.length > 0));

	$effect(() => {
		void suggestions;
		active = -1;
	});

	function readRecents(): string[] {
		try {
			const raw = localStorage.getItem(recentsKey);
			const parsed = raw ? (JSON.parse(raw) as unknown) : [];
			return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === 'string') : [];
		} catch {
			return [];
		}
	}

	function writeRecents(next: string[]) {
		recents = next;
		try {
			localStorage.setItem(recentsKey, JSON.stringify(next));
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

	function openHelp() {
		dismissed = true;
		helpOpen = true;
	}

	function openFindings() {
		dismissed = true;
		findingsOpen = true;
	}

	function submit() {
		dismissed = true;
		onSubmit?.();
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
			openHelp();
			return;
		}
		const listing = open && !showStarters && suggestions.length > 0;
		if (event.key === 'Enter') {
			event.preventDefault();
			if (listing && active >= 0 && suggestions[active]) pick(suggestions[active]);
			else submit();
			return;
		}
		if (!listing) {
			if (event.key === 'ArrowDown' && !open) dismissed = false;
			return;
		}
		if (event.key === 'ArrowDown') {
			event.preventDefault();
			active = (active + 1) % suggestions.length;
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			active = active <= 0 ? suggestions.length - 1 : active - 1;
		} else if (event.key === 'Tab') {
			event.preventDefault();
			pick(suggestions[Math.max(active, 0)]);
		}
	}
</script>

<div
	bind:this={anchor}
	class="overflow-hidden border bg-card {stuck ? 'rounded-t-none' : 'rounded-t-xl'}"
>
	<div
		class="flex h-14 items-center gap-3 px-3 transition-colors sm:px-4 {focused
			? 'bg-card'
			: 'bg-muted/30'}"
	>
		<span
			class="flex size-8 shrink-0 items-center justify-center rounded-lg transition-colors {hasError
				? 'bg-destructive/10 text-destructive'
				: focused
					? 'bg-primary text-primary-foreground shadow-sm'
					: 'bg-background text-muted-foreground ring-1 ring-border'}"
		>
			{#if busy && !hasError}
				<Spinner class="size-4" />
			{:else}
				<Search class="size-4" />
			{/if}
		</span>

		<div class="relative min-w-0 flex-1">
			<div
				bind:this={overlay}
				aria-hidden="true"
				class="pointer-events-none absolute inset-0 overflow-hidden px-0.5 whitespace-pre {TEXT}"
			>
				{#if value}
					<QueryHighlight source={value} tokens={lexed.tokens} {problems} />
				{:else}
					<span class="font-sans text-muted-foreground"
						>Search everything, or filter with
						<span class="font-mono text-muted-foreground/80">{hint}</span></span
					>
				{/if}
			</div>
			<input
				bind:this={ref}
				{value}
				type="text"
				role="combobox"
				aria-expanded={open}
				aria-controls="query-suggestions"
				aria-activedescendant={open && !showStarters && active >= 0
					? `query-option-${active}`
					: undefined}
				aria-label="Search {nounPlural}"
				autocomplete="off"
				autocapitalize="off"
				autocorrect="off"
				spellcheck={false}
				maxlength={schema.max_length}
				class="relative w-full bg-transparent px-0.5 text-transparent caret-primary outline-none selection:bg-primary/25 {TEXT}"
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

		<div class="flex shrink-0 items-center gap-1">
			{#if countLabel}
				<span class="px-1.5 text-xs text-muted-foreground tabular-nums max-sm:hidden"
					>{countLabel}</span
				>
			{/if}
			{#if value}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon"
								class="size-7 text-muted-foreground"
								aria-label="Clear search"
								onclick={() => setQuery('')}
							>
								<X class="size-4" />
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>Clear <Kbd>Esc</Kbd></Tooltip.Content>
				</Tooltip.Root>
			{:else if !focused}
				<Kbd class="max-sm:hidden">/</Kbd>
			{/if}
			<div class="mx-1 flex h-5 items-stretch max-sm:hidden">
				<Separator orientation="vertical" />
			</div>
			{#if counted}
				<Button
					variant="ghost"
					size="sm"
					class="h-8 gap-1.5 px-2 text-primary hover:bg-primary/10 hover:text-primary"
					aria-label="{findings.length} {findingWord} in this scan"
					onclick={openFindings}
				>
					<Sparkles class="size-4" />
					<span class="tabular-nums">{findings.length}</span>
					<span class="max-sm:hidden">{findingWord}</span>
				</Button>
			{/if}
			<Button
				variant="ghost"
				size="sm"
				class="h-8 gap-1.5 px-2 text-muted-foreground hover:text-foreground"
				aria-label="Search syntax reference"
				onclick={openHelp}
			>
				<CircleQuestionMark class="size-4" />
				<span class="max-sm:hidden">Syntax</span>
				{#if !value}<Kbd class="max-sm:hidden">?</Kbd>{/if}
			</Button>
		</div>
	</div>

	{#if notice}
		<div
			class="flex items-start gap-2 border-t px-4 py-1.5 text-xs {notice.level === 'error'
				? 'border-destructive/20 bg-destructive/5 text-destructive'
				: 'border-warning/20 bg-warning/5 text-warning'}"
		>
			<TriangleAlert class="mt-0.5 size-3.5 shrink-0" />
			<span>
				{notice.message}
				{#if noticeHint}<span class="text-muted-foreground">{noticeHint}</span>{/if}
			</span>
		</div>
	{/if}
</div>

<Popover.Root
	{open}
	onOpenChange={(next) => {
		if (!next) dismissed = true;
	}}
>
	<Popover.Content
		customAnchor={anchor}
		align="start"
		sideOffset={4}
		trapFocus={false}
		onOpenAutoFocus={(e) => e.preventDefault()}
		onCloseAutoFocus={(e) => e.preventDefault()}
		onmousedown={(e: MouseEvent) => e.preventDefault()}
		class="w-(--bits-popover-anchor-width) overflow-hidden p-0 shadow-lg"
	>
		<QuerySuggestions
			{noun}
			{nounPlural}
			{suggestions}
			{active}
			{recents}
			examples={starters.slice(0, EXAMPLE_LIMIT)}
			{counted}
			{showStarters}
			moreCount={Math.max(findings.length - EXAMPLE_LIMIT, 0)}
			onShowAll={openFindings}
			onPick={pick}
			onQuery={setQuery}
			onForget={(query) => writeRecents(recents.filter((r) => r !== query))}
			onHover={(index) => (active = index)}
			onHelp={openHelp}
		/>
	</Popover.Content>
</Popover.Root>

<FindingsDialog
	open={findingsOpen}
	{leadSet}
	{noun}
	{nounPlural}
	groups={schema.example_groups}
	onOpenChange={(next) => (findingsOpen = next)}
	onQuery={setQuery}
/>

<QueryHelp
	open={helpOpen}
	{schema}
	{noun}
	onOpenChange={(next) => (helpOpen = next)}
	onInsert={insertFragment}
/>
