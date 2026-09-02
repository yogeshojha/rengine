<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { EditorView, keymap, lineNumbers, highlightActiveLine } from '@codemirror/view';
	import { EditorState, StateEffect, StateField, RangeSetBuilder } from '@codemirror/state';
	import { Decoration, type DecorationSet } from '@codemirror/view';
	import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands';
	import { yaml as yamlLang } from '@codemirror/lang-yaml';
	import { linter, lintGutter, type Diagnostic } from '@codemirror/lint';
	import { autocompletion, completionKeymap, closeBrackets } from '@codemirror/autocomplete';
	import { syntaxHighlighting, HighlightStyle, indentUnit } from '@codemirror/language';
	import { tags as t } from '@lezer/highlight';
	import type { YamlIssue } from '$lib/utilities/engine-yaml';
	import { engineCompletion } from '$lib/utilities/engine-completion';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';

	interface Props {
		value: string;
		issues: YamlIssue[];
		highlight: [number, number] | null;
		onChange: (next: string) => void;
		onCursorMove?: (offset: number) => void;
	}

	let { value, issues, highlight, onChange, onCursorMove }: Props = $props();

	const engineHighlight = HighlightStyle.define([
		{
			tag: [t.comment, t.lineComment, t.blockComment],
			color: 'var(--muted-foreground)',
			fontStyle: 'italic'
		},
		{
			tag: [t.propertyName, t.definition(t.propertyName), t.labelName],
			color: 'var(--foreground)',
			fontWeight: '600'
		},
		{ tag: [t.string, t.special(t.string)], color: 'var(--info)' },
		{ tag: [t.number, t.integer, t.float], color: 'var(--info)' },
		{ tag: [t.bool, t.null, t.atom, t.keyword], color: 'var(--warning)' },
		{ tag: [t.punctuation, t.separator, t.bracket], color: 'var(--muted-foreground)' },
		{ tag: t.meta, color: 'var(--muted-foreground)' },
		{ tag: t.invalid, color: 'var(--destructive)' }
	]);

	let host: HTMLDivElement;
	let view: EditorView | undefined;
	let current = $state('');

	const setFlash = StateEffect.define<[number, number] | null>();
	const flashField = StateField.define<DecorationSet>({
		create: () => Decoration.none,
		update(deco, tr) {
			deco = deco.map(tr.changes);
			for (const effect of tr.effects) {
				if (!effect.is(setFlash)) continue;
				const range = effect.value;
				if (!range) return Decoration.none;
				const builder = new RangeSetBuilder<Decoration>();
				const from = Math.min(range[0], tr.state.doc.length);
				const to = Math.min(range[1], tr.state.doc.length);
				if (from < to) {
					builder.add(from, to, Decoration.mark({ class: 'cm-engine-focus' }));
				}
				return builder.finish();
			}
			return deco;
		},
		provide: (f) => EditorView.decorations.from(f)
	});

	let latestIssues = $state<YamlIssue[]>([]);
	$effect(() => {
		latestIssues = issues;
		untrack(() => view?.dispatch({}));
	});

	function diagnostics(): Diagnostic[] {
		const length = view?.state.doc.length ?? 0;
		return latestIssues.map((issue) => ({
			from: Math.min(issue.from, length),
			to: Math.min(Math.max(issue.to, issue.from + 1), length),
			severity: issue.severity,
			message: issue.message
		}));
	}

	onMount(() => {
		current = value;
		view = new EditorView({
			parent: host,
			state: EditorState.create({
				doc: value,
				extensions: [
					lineNumbers(),
					history(),
					highlightActiveLine(),
					yamlLang(),
					syntaxHighlighting(engineHighlight, { fallback: true }),
					indentUnit.of('  '),
					lintGutter(),
					linter(diagnostics, { delay: 200 }),
					closeBrackets(),
					autocompletion({
						override: [engineCompletion(() => engineCatalogStore.catalog)],
						activateOnTyping: true,
						icons: false,
						defaultKeymap: false
					}),
					flashField,
					keymap.of([...completionKeymap, ...defaultKeymap, ...historyKeymap, indentWithTab]),
					EditorView.lineWrapping,
					EditorView.updateListener.of((update) => {
						if (update.docChanged) {
							current = update.state.doc.toString();
							onChange(current);
						}
						if (update.selectionSet && onCursorMove) {
							onCursorMove(update.state.selection.main.head);
						}
					}),
					EditorView.theme({
						'&': {
							height: '100%',
							fontSize: '12.5px',
							backgroundColor: 'transparent',
							color: 'var(--foreground)'
						},
						'.cm-content': { caretColor: 'var(--foreground)' },
						'.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--foreground)' },
						'.cm-selectionBackground, ::selection': {
							backgroundColor: 'color-mix(in oklch, var(--foreground) 16%, transparent)'
						},
						'&.cm-focused .cm-selectionBackground': {
							backgroundColor: 'color-mix(in oklch, var(--foreground) 22%, transparent)'
						},
						'.cm-activeLineGutter': { backgroundColor: 'transparent', color: 'var(--foreground)' },
						'.cm-lintRange-error': {
							backgroundImage: 'none',
							borderBottom: '1px wavy var(--destructive)',
							textDecoration: 'underline wavy var(--destructive)'
						},
						'.cm-lintRange-warning': {
							backgroundImage: 'none',
							textDecoration: 'underline wavy var(--warning)'
						},
						'.cm-tooltip': {
							backgroundColor: 'var(--popover)',
							color: 'var(--popover-foreground)',
							border: '1px solid var(--border)',
							borderRadius: '6px',
							fontSize: '11.5px'
						},
						'.cm-tooltip .cm-diagnostic': { padding: '4px 8px', borderLeft: 'none' },
						'.cm-tooltip.cm-tooltip-autocomplete > ul': {
							fontFamily: 'var(--font-mono, ui-monospace, monospace)',
							maxHeight: '15em'
						},
						'.cm-tooltip.cm-tooltip-autocomplete > ul > li': { padding: '3px 8px' },
						'.cm-tooltip-autocomplete ul li[aria-selected]': {
							backgroundColor: 'var(--accent)',
							color: 'var(--accent-foreground)'
						},
						'.cm-completionDetail': {
							fontStyle: 'normal',
							opacity: '0.6',
							marginLeft: '10px',
							fontSize: '10.5px'
						},
						'.cm-completionInfo': {
							backgroundColor: 'var(--popover)',
							color: 'var(--popover-foreground)',
							border: '1px solid var(--border)',
							borderRadius: '6px',
							padding: '6px 9px',
							maxWidth: '280px',
							fontFamily: 'var(--font-sans)',
							fontSize: '11.5px',
							lineHeight: '1.5'
						},
						'.cm-scroller': {
							fontFamily: 'var(--font-mono, ui-monospace, monospace)',
							lineHeight: '1.6'
						},
						'&.cm-focused': { outline: 'none' },
						'.cm-gutters': {
							backgroundColor: 'transparent',
							border: 'none',
							color: 'var(--muted-foreground)',
							opacity: '0.55'
						},
						'.cm-activeLine': {
							backgroundColor: 'color-mix(in oklch, var(--muted) 55%, transparent)'
						},
						'.cm-engine-focus': {
							backgroundColor: 'color-mix(in oklch, var(--foreground) 9%, transparent)',
							borderRadius: '3px'
						}
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
			view.dispatch({
				changes: { from: 0, to: view.state.doc.length, insert: next }
			});
		});
	});

	$effect(() => {
		const range = highlight;
		untrack(() => {
			if (!view) return;
			const effects: StateEffect<unknown>[] = [setFlash.of(range)];
			if (range) {
				const to = Math.min(range[1], view.state.doc.length);
				effects.push(
					EditorView.scrollIntoView(Math.min(range[0], to), { y: 'start', yMargin: 24 })
				);
			}
			view.dispatch({ effects });
		});
	});
</script>

<div class="yaml-pane" bind:this={host}></div>

<style>
	.yaml-pane {
		height: 100%;
		min-height: 0;
		overflow: hidden;
	}
	.yaml-pane :global(.cm-editor) {
		height: 100%;
	}
</style>
