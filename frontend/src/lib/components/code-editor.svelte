<script lang="ts" module>
	export type EditorLang = 'http' | 'text';
</script>

<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { EditorView, keymap, drawSelection, placeholder as hintText } from '@codemirror/view';
	import { EditorState } from '@codemirror/state';
	import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
	import ArrowLeftRight from '@lucide/svelte/icons/arrow-left-right';
	import FileText from '@lucide/svelte/icons/file-text';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import CopyButton from '$lib/components/copy-button.svelte';
	import { codeTokens } from '$lib/utilities/code-theme';
	import { LANG_LABELS } from '$lib/utilities/code-highlight';
	import { cn } from '$lib/utils';

	interface Props {
		value: string;
		lang?: EditorLang;
		label?: string;
		rows?: number;
		placeholder?: string;
		onSubmit?: () => void;
		class?: string;
	}

	let {
		value = $bindable(''),
		lang = 'text',
		label,
		rows = 18,
		placeholder = '',
		onSubmit,
		class: className
	}: Props = $props();

	const Icon = $derived(lang === 'http' ? ArrowLeftRight : FileText);
	const name = $derived(label ?? LANG_LABELS[lang]);

	let host: HTMLDivElement;
	let view: EditorView | undefined;
	let current = '';

	/** Puts the cursor at an offset, the end when none is given. */
	export function focus(offset?: number) {
		if (!view) return;
		const at = Math.min(offset ?? view.state.doc.length, view.state.doc.length);
		view.dispatch({ selection: { anchor: at }, scrollIntoView: true });
		view.focus();
	}

	onMount(() => {
		current = value;
		view = new EditorView({
			parent: host,
			state: EditorState.create({
				doc: value,
				extensions: [
					history(),
					drawSelection(),
					...(lang === 'text' ? [] : [codeTokens(lang)]),
					hintText(placeholder),
					keymap.of([
						{
							key: 'Mod-Enter',
							run: () => {
								if (!onSubmit) return false;
								onSubmit();
								return true;
							}
						},
						...defaultKeymap,
						...historyKeymap
					]),
					EditorView.lineWrapping,
					EditorView.contentAttributes.of({
						spellcheck: 'false',
						autocorrect: 'off',
						autocapitalize: 'off',
						'aria-label': name
					}),
					EditorView.updateListener.of((update) => {
						if (!update.docChanged) return;
						current = update.state.doc.toString();
						value = current;
					}),
					EditorView.theme({
						'&': {
							height: 'auto',
							flex: '1 0 auto',
							fontSize: '12px',
							backgroundColor: 'transparent',
							color: 'var(--code-fg)'
						},
						'.cm-scroller': {
							fontFamily: 'var(--font-mono, ui-monospace, monospace)',
							lineHeight: '1.65',
							height: 'auto',
							flex: '1 0 auto',
							overflow: 'visible'
						},
						'.cm-content': { caretColor: 'var(--foreground)', padding: '8px 0' },
						'.cm-line': { padding: '0 14px' },
						'.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--foreground)' },
						'&.cm-focused': { outline: 'none' },
						'.cm-selectionBackground, ::selection': {
							backgroundColor: 'color-mix(in oklch, var(--primary) 18%, transparent)'
						},
						'&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
							backgroundColor: 'color-mix(in oklch, var(--primary) 24%, transparent)'
						},
						'.cm-placeholder': { color: 'var(--muted-foreground)' }
					})
				]
			})
		});
		return () => view?.destroy();
	});

	$effect(() => {
		const next = value;
		untrack(() => {
			if (!view || next === current) return;
			current = next;
			view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: next } });
		});
	});
</script>

<div
	class={cn('code-editor flex min-w-0 flex-col overflow-hidden rounded-lg border', className)}
	style="--ce-rows:{rows}"
>
	<div class="ce-bar">
		<Icon class="size-3.5 shrink-0 text-muted-foreground" />
		<span class="truncate font-medium">{name}</span>
		<div class="ml-auto flex shrink-0 items-center">
			<CopyButton {value} />
		</div>
	</div>
	<div class="ce-body">
		<ScrollArea class="h-full" scrollbarYClasses="w-1.5">
			<div class="ce-host" bind:this={host}></div>
		</ScrollArea>
	</div>
</div>

<style>
	.code-editor {
		background: var(--code-surface);
		color: var(--code-fg);
	}
	.ce-bar {
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
	.ce-body {
		height: min(calc(var(--ce-rows) * 1.65 * 12px + 16px), 55dvh);
		min-height: 0;
	}
	.ce-body :global([data-scroll-area-content]) {
		display: flex;
		flex-direction: column;
		min-height: 100%;
	}
	.ce-host {
		display: flex;
		flex-direction: column;
		flex: 1 0 auto;
		min-width: 0;
	}
</style>
