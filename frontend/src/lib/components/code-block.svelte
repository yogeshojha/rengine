<script lang="ts">
	import type { Snippet } from 'svelte';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Button } from '$lib/components/ui/button';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import Download from '@lucide/svelte/icons/download';
	import TextWrap from '@lucide/svelte/icons/text-wrap';
	import WandSparkles from '@lucide/svelte/icons/wand-sparkles';
	import FileCode from '@lucide/svelte/icons/file-code';
	import Braces from '@lucide/svelte/icons/braces';
	import ArrowLeftRight from '@lucide/svelte/icons/arrow-left-right';
	import Terminal from '@lucide/svelte/icons/terminal';
	import FileText from '@lucide/svelte/icons/file-text';
	import CodeXml from '@lucide/svelte/icons/code-xml';
	import Code from '@lucide/svelte/icons/code';
	import Palette from '@lucide/svelte/icons/palette';
	import { downloadBlob } from '$lib/utilities/download';
	import {
		highlight,
		applyMarks,
		prettify,
		LANG_LABELS,
		type CodeLang
	} from '$lib/utilities/code-highlight';
	import type { IconComponent } from '$lib/config/icons';
	import { cn } from '$lib/utils';

	interface Props {
		code: string;
		lang?: CodeLang;
		label?: string;
		numbers?: boolean;
		wrap?: boolean;
		maxLines?: number;
		maxHeight?: string;
		toolbar?: boolean;
		copy?: boolean;
		download?: string;
		marks?: string[];
		emptyText?: string;
		class?: string;
		actions?: Snippet;
	}

	let {
		code,
		lang = 'text',
		label,
		numbers,
		wrap,
		maxLines = 18,
		maxHeight = '26rem',
		toolbar = true,
		copy = true,
		download,
		marks = [],
		emptyText,
		class: className,
		actions
	}: Props = $props();

	const LANG_ICONS: Record<CodeLang, IconComponent> = {
		yaml: FileCode,
		json: Braces,
		http: ArrowLeftRight,
		shell: Terminal,
		html: CodeXml,
		xml: CodeXml,
		css: Palette,
		js: Code,
		text: FileText
	};
	const WRAPS: Record<CodeLang, boolean> = {
		yaml: false,
		json: false,
		http: true,
		shell: true,
		html: true,
		xml: true,
		css: false,
		js: true,
		text: true
	};
	const AUTO_NUMBERS = 6;
	const MAX_RENDER = 4000;

	let expanded = $state(false);
	let wrapOverride = $state<boolean | null>(null);
	let pretty = $state(false);
	let viewport = $state<HTMLElement | null>(null);
	let scrollable = $state(false);

	const raw = $derived(code ?? '');
	const formatted = $derived(prettify(raw, lang));
	const source = $derived(pretty && formatted ? formatted : raw);
	const lines = $derived(
		marks.length ? applyMarks(highlight(source, lang), marks) : highlight(source, lang)
	);
	const total = $derived(lines.length);
	const collapsible = $derived(maxLines > 0 && total > maxLines);
	const shown = $derived(
		collapsible && !expanded ? lines.slice(0, maxLines) : lines.slice(0, MAX_RENDER)
	);
	const hidden = $derived(total - shown.length);
	const wrapped = $derived(wrapOverride ?? wrap ?? WRAPS[lang]);
	const gutter = $derived(numbers ?? total > AUTO_NUMBERS);
	const width = $derived(`${String(total).length + 1}ch`);
	const Icon = $derived(LANG_ICONS[lang]);

	$effect(() => {
		void shown;
		void wrapped;
		const el = viewport;
		if (!el) return;
		const measure = () => {
			scrollable = el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1;
		};
		measure();
		const observer = new ResizeObserver(measure);
		observer.observe(el);
		return () => observer.disconnect();
	});
</script>

{#if source}
	<div
		class={cn('code-block flex min-w-0 flex-col overflow-hidden rounded-lg border', className)}
		style="--cb-max:{maxHeight};--cb-gutter:{width}"
	>
		{#if toolbar}
			<div class="cb-bar">
				<Icon class="size-3.5 shrink-0 text-muted-foreground" />
				<span class="truncate font-medium">{label ?? LANG_LABELS[lang]}</span>
				{#if total > 1}
					<span class="shrink-0 text-muted-foreground tabular-nums">
						{total.toLocaleString()} lines
					</span>
				{/if}
				{#if pretty}
					<span class="shrink-0 text-muted-foreground">formatted</span>
				{/if}
				<div class="ml-auto flex shrink-0 items-center gap-0.5">
					{@render actions?.()}
					{#if formatted}
						<Hint text={pretty ? 'Show it as it was received' : 'Format for reading'}>
							{#snippet child(props)}
								<Button
									{...props}
									variant="ghost"
									size="icon"
									class={pretty ? 'size-7 text-foreground' : 'size-7 text-muted-foreground'}
									aria-pressed={pretty}
									onclick={() => (pretty = !pretty)}
								>
									<WandSparkles class="size-3.5" />
								</Button>
							{/snippet}
						</Hint>
					{/if}
					<Hint text={wrapped ? 'Do not wrap lines' : 'Wrap lines'}>
						{#snippet child(props)}
							<Button
								{...props}
								variant="ghost"
								size="icon"
								class={wrapped ? 'size-7 text-foreground' : 'size-7 text-muted-foreground'}
								aria-pressed={wrapped}
								onclick={() => (wrapOverride = !wrapped)}
							>
								<TextWrap class="size-3.5" />
							</Button>
						{/snippet}
					</Hint>
					{#if download}
						<Hint text="Download">
							{#snippet child(props)}
								<Button
									{...props}
									variant="ghost"
									size="icon"
									class="size-7 text-muted-foreground"
									onclick={() => downloadBlob(download!, source)}
								>
									<Download class="size-3.5" />
								</Button>
							{/snippet}
						</Hint>
					{/if}
					{#if copy}
						<CopyButton value={source} />
					{/if}
				</div>
			</div>
		{/if}

		<div class="cb-body">
			<ScrollArea
				bind:viewportRef={viewport}
				orientation="both"
				class="cb-scroll"
				scrollbarXClasses="h-1.5"
				scrollbarYClasses="w-1.5"
			>
				<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
				<div
					class="cb-code"
					class:wrapped
					role={scrollable ? 'group' : undefined}
					tabindex={scrollable ? 0 : undefined}
					aria-label={scrollable ? `${label ?? LANG_LABELS[lang]}, scrollable` : undefined}
				>
					{#each shown as line, index (index)}
						<!-- prettier-ignore -->
						<div class="cb-line">{#if gutter}<span class="cb-ln" aria-hidden="true">{index + 1}</span>{/if}<span class="cb-lc">{#each line as token, at (at)}<span class="t-{token.kind}" class:mark={token.mark}>{token.text}</span>{/each}</span></div>
					{/each}
				</div>
			</ScrollArea>
			{#if collapsible && !expanded}
				<div class="cb-fade" aria-hidden="true"></div>
			{/if}
		</div>

		{#if collapsible}
			<button type="button" class="cb-more" onclick={() => (expanded = !expanded)}>
				{#if expanded}
					<ChevronUp class="size-3.5" />
					Show less
				{:else}
					<ChevronDown class="size-3.5" />
					Show all {total.toLocaleString()} lines
				{/if}
			</button>
		{:else if hidden > 0}
			<div class="cb-more cursor-default">
				{hidden.toLocaleString()} more lines not shown
			</div>
		{/if}
	</div>
{:else if emptyText}
	<div
		class={cn(
			'rounded-lg border border-dashed px-3 py-6 text-center text-xs text-muted-foreground',
			className
		)}
	>
		{emptyText}
	</div>
{/if}

<style>
	.code-block {
		background: var(--code-surface);
		color: var(--code-fg);
	}
	.cb-bar {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		height: 2.25rem;
		flex-shrink: 0;
		padding: 0 0.375rem 0 0.75rem;
		border-bottom: 1px solid var(--border);
		font-size: 11px;
		line-height: 1;
	}
	.cb-body {
		position: relative;
		min-height: 0;
	}
	.cb-body :global([data-slot='scroll-area-viewport']) {
		max-height: var(--cb-max);
	}
	.cb-code {
		font-family: var(--font-mono);
		font-size: 12px;
		line-height: 1.65;
		padding: 0.5rem 0;
		min-width: max-content;
		tab-size: 4;
	}
	.cb-code.wrapped {
		min-width: 0;
		width: 100%;
	}
	.cb-code:focus-visible {
		outline: 2px solid var(--ring);
		outline-offset: -2px;
	}
	.cb-line {
		display: flex;
		align-items: flex-start;
		min-height: 1.65em;
	}
	.cb-ln {
		position: sticky;
		left: 0;
		z-index: 1;
		flex-shrink: 0;
		width: calc(var(--cb-gutter) + 1.25rem);
		padding-right: 0.75rem;
		text-align: right;
		color: var(--code-gutter);
		background: var(--code-surface);
		font-variant-numeric: tabular-nums;
		user-select: none;
		-webkit-user-select: none;
	}
	.cb-lc {
		white-space: pre;
		padding-right: 1rem;
	}
	.cb-code:not(.wrapped) .cb-lc {
		flex: 0 0 auto;
	}
	.cb-code.wrapped .cb-lc {
		flex: 1 1 auto;
		min-width: 0;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}
	.cb-lc:first-child {
		padding-left: 0.875rem;
	}
	.cb-fade {
		position: absolute;
		inset-inline: 0;
		bottom: 0;
		height: 2.75rem;
		pointer-events: none;
		background: linear-gradient(to bottom, transparent, var(--code-surface) 85%);
	}
	.cb-more {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.375rem;
		flex-shrink: 0;
		height: 2rem;
		border-top: 1px solid var(--border);
		font-size: 11px;
		color: var(--muted-foreground);
		transition:
			color 0.12s ease,
			background-color 0.12s ease;
	}
	button.cb-more:hover {
		color: var(--foreground);
		background: color-mix(in oklch, var(--accent) 45%, transparent);
	}
	button.cb-more:focus-visible {
		outline: 2px solid var(--ring);
		outline-offset: -2px;
	}

	.cb-code :global(.t-comment) {
		color: var(--code-comment);
		font-style: italic;
	}
	.cb-code :global(.t-key) {
		color: var(--code-key);
		font-weight: 600;
	}
	.cb-code :global(.t-string),
	.cb-code :global(.t-scalar) {
		color: var(--code-string);
	}
	.cb-code :global(.t-number) {
		color: var(--code-number);
	}
	.cb-code :global(.t-atom) {
		color: var(--code-atom);
	}
	.cb-code :global(.t-keyword) {
		color: var(--code-keyword);
		font-weight: 500;
	}
	.cb-code :global(.t-punct) {
		color: var(--code-punct);
	}
	.cb-code :global(.t-meta) {
		color: var(--code-meta);
	}
	.cb-code :global(.t-link) {
		color: var(--code-link);
		text-decoration: underline;
		text-decoration-color: color-mix(in oklch, var(--code-link) 40%, transparent);
		text-underline-offset: 2px;
	}
	.cb-code :global(.t-tag) {
		color: var(--code-tag);
		font-weight: 500;
	}
	.cb-code :global(.t-attr) {
		color: var(--code-attr);
	}
	.cb-code :global(.t-fn) {
		color: var(--code-fn);
	}
	.cb-code :global(.t-op) {
		color: var(--code-op);
	}
	.cb-code :global(.t-invalid) {
		color: var(--destructive);
	}
	.cb-code :global(.t-ok) {
		color: var(--success);
		font-weight: 600;
	}
	.cb-code :global(.t-redir) {
		color: var(--info);
		font-weight: 600;
	}
	.cb-code :global(.t-warn) {
		color: var(--warning);
		font-weight: 600;
	}
	.cb-code :global(.t-err) {
		color: var(--destructive);
		font-weight: 600;
	}
	.cb-code :global(.mark) {
		border-radius: 2px;
		background: var(--code-mark);
		box-shadow: 0 0 0 1.5px var(--code-mark);
	}
</style>
