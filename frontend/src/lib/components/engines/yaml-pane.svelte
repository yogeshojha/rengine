<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import {
		EditorView,
		keymap,
		lineNumbers,
		highlightActiveLine,
		highlightActiveLineGutter,
		drawSelection,
		gutter,
		GutterMarker,
		Decoration,
		MatchDecorator,
		ViewPlugin,
		type DecorationSet,
		type ViewUpdate
	} from '@codemirror/view';
	import {
		EditorState,
		StateEffect,
		StateField,
		RangeSet,
		RangeSetBuilder,
		Compartment
	} from '@codemirror/state';
	import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands';
	import { yaml as yamlLang } from '@codemirror/lang-yaml';
	import { linter, lintGutter, type Diagnostic } from '@codemirror/lint';
	import { autocompletion, completionKeymap, closeBrackets } from '@codemirror/autocomplete';
	import {
		syntaxHighlighting,
		HighlightStyle,
		indentUnit,
		foldGutter,
		foldKeymap,
		bracketMatching,
		indentOnInput
	} from '@codemirror/language';
	import { highlightSelectionMatches, searchKeymap } from '@codemirror/search';
	import { tags as t } from '@lezer/highlight';
	import * as Breadcrumb from '$lib/components/ui/breadcrumb';
	import * as Kbd from '$lib/components/ui/kbd';
	import { Button } from '$lib/components/ui/button';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleAlert from '@lucide/svelte/icons/circle-alert';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import FileCode2 from '@lucide/svelte/icons/file-code';
	import { parse, pathAtOffset, stageBlocks, type YamlIssue } from '$lib/utilities/engine-yaml';
	import { engineCompletion } from '$lib/utilities/engine-completion';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';

	interface Props {
		value: string;
		issues?: YamlIssue[];
		activeStage?: string | null;
		stageStates?: Record<string, boolean>;
		reveal?: number;
		readonly?: boolean;
		chrome?: boolean;
		onChange?: (next: string) => void;
		onCursorMove?: (offset: number) => void;
		onToggleStage?: (name: string) => void;
	}

	let {
		value,
		issues = [],
		activeStage = null,
		stageStates = {},
		reveal = 0,
		readonly = false,
		chrome = true,
		onChange,
		onCursorMove,
		onToggleStage
	}: Props = $props();

	const engineHighlight = HighlightStyle.define([
		{
			tag: [t.comment, t.lineComment, t.blockComment],
			color: 'var(--muted-foreground)',
			fontStyle: 'italic'
		},
		{
			tag: [t.propertyName, t.definition(t.propertyName), t.labelName],
			color: 'var(--foreground)',
			fontWeight: '500'
		},
		{ tag: [t.content, t.string, t.special(t.string)], color: 'var(--chart-1)' },
		{ tag: [t.number, t.integer, t.float], color: 'var(--chart-4)' },
		{ tag: [t.bool, t.null, t.atom, t.keyword], color: 'var(--chart-3)' },
		{
			tag: [t.punctuation, t.separator, t.bracket, t.brace, t.squareBracket],
			color: 'var(--muted-foreground)'
		},
		{ tag: [t.meta, t.typeName], color: 'var(--muted-foreground)' },
		{ tag: t.invalid, color: 'var(--destructive)' }
	]);

	const scalarKinds = new MatchDecorator({
		regexp: /^(\s*(?:[\w-]+:\s+|-\s+))(true|false|null|~|-?\d+(?:\.\d+)?)\s*$/g,
		decorate(add, from, _to, match) {
			const start = from + match[1].length;
			const kind = /^(true|false|null|~)$/.test(match[2]) ? 'cm-yaml-bool' : 'cm-yaml-num';
			add(start, start + match[2].length, Decoration.mark({ class: kind }));
		}
	});
	const scalarPlugin = ViewPlugin.fromClass(
		class {
			decorations: DecorationSet;
			constructor(view: EditorView) {
				this.decorations = scalarKinds.createDeco(view);
			}
			update(update: ViewUpdate) {
				this.decorations = scalarKinds.updateDeco(update, this.decorations);
			}
		},
		{ decorations: (v) => v.decorations }
	);

	class StageMarker extends GutterMarker {
		name: string;
		enabled: boolean;
		constructor(name: string, enabled: boolean) {
			super();
			this.name = name;
			this.enabled = enabled;
		}
		eq(other: StageMarker) {
			return other.name === this.name && other.enabled === this.enabled;
		}
		toDOM() {
			const el = document.createElement('span');
			el.className = `cm-stage-dot${this.enabled ? ' on' : ''}`;
			el.title = `${this.name}: ${this.enabled ? 'on' : 'off'}`;
			return el;
		}
	}

	interface Block {
		name: string;
		from: number;
		to: number;
		enabled: boolean;
		active: boolean;
	}
	const setBlocks = StateEffect.define<Block[]>();

	const stageMarkers = StateField.define<RangeSet<GutterMarker>>({
		create: () => RangeSet.empty,
		update(set, tr) {
			set = set.map(tr.changes);
			for (const effect of tr.effects) {
				if (!effect.is(setBlocks)) continue;
				const builder = new RangeSetBuilder<GutterMarker>();
				const length = tr.state.doc.length;
				for (const block of [...effect.value].sort((a, b) => a.from - b.from)) {
					const line = tr.state.doc.lineAt(Math.min(block.from, length));
					builder.add(line.from, line.from, new StageMarker(block.name, block.enabled));
				}
				set = builder.finish();
			}
			return set;
		}
	});

	const activeLine = Decoration.line({ class: 'cm-stage-active' });
	const stageKey = Decoration.mark({ class: 'cm-stage-key' });
	const blockDecorations = StateField.define<DecorationSet>({
		create: () => Decoration.none,
		update(deco, tr) {
			deco = deco.map(tr.changes);
			for (const effect of tr.effects) {
				if (!effect.is(setBlocks)) continue;
				const builder = new RangeSetBuilder<Decoration>();
				const doc = tr.state.doc;
				for (const block of [...effect.value].sort((a, b) => a.from - b.from)) {
					const from = Math.min(block.from, doc.length);
					const to = Math.min(block.to, doc.length);
					const first = doc.lineAt(from);
					const last = doc.lineAt(to);
					for (let n = first.number; n <= last.number; n++) {
						const line = doc.line(n);
						if (block.active) builder.add(line.from, line.from, activeLine);
						if (n === first.number && block.name.length) {
							builder.add(from, Math.min(from + block.name.length, line.to), stageKey);
						}
					}
				}
				deco = builder.finish();
			}
			return deco;
		},
		provide: (f) => EditorView.decorations.from(f)
	});

	const stageGutter = gutter({
		class: 'cm-stage-gutter',
		markers: (view) => view.state.field(stageMarkers),
		domEventHandlers: {
			mousedown(view, line) {
				const cursor = view.state.field(stageMarkers).iter(line.from);
				if (cursor.value && cursor.from === line.from) {
					onToggleStage?.((cursor.value as StageMarker).name);
					return true;
				}
				return false;
			}
		}
	});

	const readOnlyCompartment = new Compartment();

	let host: HTMLDivElement;
	let view: EditorView | undefined;
	let current = $state('');
	let cursorLine = $state(1);
	let cursorCol = $state(1);
	let cursorPath = $state<string[]>([]);

	let latestIssues = $state<YamlIssue[]>([]);
	$effect(() => {
		latestIssues = issues;
		untrack(() => view?.dispatch({}));
	});

	const errorCount = $derived(issues.filter((i) => i.severity === 'error').length);
	const warningCount = $derived(issues.length - errorCount);
	const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform);
	const mod = isMac ? '⌘' : 'Ctrl';

	function diagnostics(): Diagnostic[] {
		const length = view?.state.doc.length ?? 0;
		return latestIssues.map((issue) => ({
			from: Math.min(issue.from, length),
			to: Math.min(Math.max(issue.to, issue.from + 1), length),
			severity: issue.severity,
			message: issue.message
		}));
	}

	function jumpToFirstIssue() {
		const first = [...latestIssues].sort((a, b) => a.from - b.from)[0];
		if (!view || !first) return;
		const pos = Math.min(first.from, view.state.doc.length);
		view.dispatch({ selection: { anchor: pos }, scrollIntoView: true });
		view.focus();
	}

	function syncBlocks() {
		if (!view) return;
		const doc = parse(current);
		const blocks: Block[] = stageBlocks(doc).map((b) => ({
			...b,
			enabled: stageStates[b.name] ?? true,
			active: b.name === activeStage
		}));
		view.dispatch({ effects: setBlocks.of(blocks) });
	}

	function updateCursor(offset: number) {
		if (!view) return;
		const line = view.state.doc.lineAt(offset);
		cursorLine = line.number;
		cursorCol = offset - line.from + 1;
		if (chrome) cursorPath = pathAtOffset(parse(current), offset);
	}

	onMount(() => {
		current = value;
		view = new EditorView({
			parent: host,
			state: EditorState.create({
				doc: value,
				extensions: [
					lineNumbers(),
					stageGutter,
					foldGutter({
						markerDOM(open) {
							const el = document.createElement('span');
							el.className = 'cm-fold-mark';
							el.textContent = open ? '⌄' : '›';
							return el;
						}
					}),
					highlightActiveLineGutter(),
					history(),
					drawSelection(),
					highlightActiveLine(),
					highlightSelectionMatches(),
					bracketMatching(),
					indentOnInput(),
					yamlLang(),
					syntaxHighlighting(engineHighlight, { fallback: true }),
					scalarPlugin,
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
					stageMarkers,
					blockDecorations,
					readOnlyCompartment.of([
						EditorState.readOnly.of(readonly),
						EditorView.editable.of(!readonly)
					]),
					keymap.of([
						...completionKeymap,
						...searchKeymap,
						...foldKeymap,
						...defaultKeymap,
						...historyKeymap,
						indentWithTab
					]),
					EditorView.lineWrapping,
					EditorView.updateListener.of((update) => {
						if (update.docChanged) {
							current = update.state.doc.toString();
							onChange?.(current);
						}
						if (update.selectionSet || update.docChanged) {
							const head = update.state.selection.main.head;
							updateCursor(head);
							if (update.selectionSet) onCursorMove?.(head);
						}
					}),
					EditorView.theme({
						'&': {
							height: '100%',
							fontSize: '13px',
							backgroundColor: 'transparent',
							color: 'var(--foreground)'
						},
						'.cm-scroller': {
							fontFamily: 'var(--font-mono, ui-monospace, monospace)',
							lineHeight: '1.7'
						},
						'.cm-content': { caretColor: 'var(--foreground)', padding: '10px 0 32px' },
						'.cm-line': { padding: '0 14px 0 6px' },
						'.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--foreground)' },
						'&.cm-focused': { outline: 'none' },
						'.cm-selectionBackground, ::selection': {
							backgroundColor: 'color-mix(in oklch, var(--primary) 18%, transparent)'
						},
						'&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
							backgroundColor: 'color-mix(in oklch, var(--primary) 24%, transparent)'
						},
						'.cm-selectionMatch': {
							backgroundColor: 'color-mix(in oklch, var(--foreground) 10%, transparent)'
						},
						'.cm-matchingBracket': {
							backgroundColor: 'color-mix(in oklch, var(--primary) 16%, transparent)',
							outline: 'none'
						},
						'.cm-activeLine': {
							backgroundColor: 'color-mix(in oklch, var(--muted) 60%, transparent)'
						},
						'.cm-stage-active': {
							backgroundColor: 'color-mix(in oklch, var(--primary) 5%, transparent)',
							boxShadow: 'inset 2px 0 0 color-mix(in oklch, var(--primary) 55%, transparent)'
						},
						'.cm-gutters': {
							backgroundColor: 'transparent',
							border: 'none',
							color: 'var(--muted-foreground)',
							paddingLeft: '6px'
						},
						'.cm-lineNumbers .cm-gutterElement': {
							minWidth: '28px',
							opacity: '0.55',
							fontSize: '11.5px'
						},
						'.cm-activeLineGutter': { backgroundColor: 'transparent' },
						'.cm-lineNumbers .cm-activeLineGutter': { opacity: '1', color: 'var(--foreground)' },
						'.cm-stage-gutter .cm-gutterElement': { width: '14px' },
						'.cm-foldGutter .cm-gutterElement': { width: '14px', cursor: 'pointer' },
						'.cm-lintRange-error': {
							backgroundImage: 'none',
							textDecoration: 'underline wavy var(--destructive)',
							textUnderlineOffset: '3px'
						},
						'.cm-lintRange-warning': {
							backgroundImage: 'none',
							textDecoration: 'underline wavy var(--warning)',
							textUnderlineOffset: '3px'
						},
						'.cm-gutter-lint .cm-gutterElement': { padding: '0 2px 0 0' },
						'.cm-tooltip': {
							backgroundColor: 'var(--popover)',
							color: 'var(--popover-foreground)',
							border: '1px solid var(--border)',
							borderRadius: '8px',
							boxShadow: 'var(--shadow-md)',
							fontSize: '12px'
						},
						'.cm-tooltip .cm-diagnostic': { padding: '5px 9px', borderLeft: 'none' },
						'.cm-tooltip.cm-tooltip-autocomplete > ul': {
							fontFamily: 'var(--font-mono, ui-monospace, monospace)',
							maxHeight: '16em'
						},
						'.cm-tooltip.cm-tooltip-autocomplete > ul > li': { padding: '4px 10px' },
						'.cm-tooltip-autocomplete ul li[aria-selected]': {
							backgroundColor: 'var(--accent)',
							color: 'var(--accent-foreground)'
						},
						'.cm-completionDetail': {
							fontStyle: 'normal',
							opacity: '0.6',
							marginLeft: '10px',
							fontSize: '11px'
						},
						'.cm-completionInfo': {
							backgroundColor: 'var(--popover)',
							color: 'var(--popover-foreground)',
							border: '1px solid var(--border)',
							borderRadius: '8px',
							padding: '7px 10px',
							maxWidth: '300px',
							fontFamily: 'var(--font-sans)',
							fontSize: '12px',
							lineHeight: '1.5'
						},
						'.cm-panels': {
							backgroundColor: 'var(--card)',
							color: 'var(--foreground)',
							borderColor: 'var(--border)'
						},
						'.cm-panels.cm-panels-top': { borderBottom: '1px solid var(--border)' },
						'.cm-panel.cm-search': { padding: '6px 10px', fontFamily: 'var(--font-sans)' },
						'.cm-panel.cm-search input, .cm-panel.cm-search button': {
							fontSize: '12px',
							borderRadius: '6px',
							border: '1px solid var(--input)',
							backgroundColor: 'var(--background)',
							color: 'var(--foreground)',
							padding: '3px 8px',
							margin: '0 4px 0 0'
						},
						'.cm-panel.cm-search label': { fontSize: '12px', marginRight: '8px' },
						'.cm-panel.cm-search button[name=close]': { color: 'var(--muted-foreground)' }
					})
				]
			})
		});
		updateCursor(0);
		syncBlocks();
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

	$effect(() => {
		void current;
		void activeStage;
		void stageStates;
		untrack(syncBlocks);
	});

	$effect(() => {
		const token = reveal;
		const name = activeStage;
		untrack(() => {
			if (!view || !token || !name) return;
			const block = stageBlocks(parse(current)).find((b) => b.name === name);
			if (!block) return;
			view.dispatch({
				effects: EditorView.scrollIntoView(Math.min(block.from, view.state.doc.length), {
					y: 'start',
					yMargin: 28
				})
			});
		});
	});

	$effect(() => {
		const ro = readonly;
		untrack(() => {
			view?.dispatch({
				effects: readOnlyCompartment.reconfigure([
					EditorState.readOnly.of(ro),
					EditorView.editable.of(!ro)
				])
			});
		});
	});
</script>

<div class="yaml-pane">
	{#if chrome}
		<div class="crumbs">
			<Breadcrumb.Root>
				<Breadcrumb.List class="gap-1 text-[11px] sm:gap-1">
					<Breadcrumb.Item class="gap-1 text-muted-foreground">
						<FileCode2 size={12} />
						engine.yaml
					</Breadcrumb.Item>
					{#each cursorPath as segment, i (i)}
						<Breadcrumb.Separator class="[&>svg]:size-3" />
						<Breadcrumb.Item>
							{#if i === cursorPath.length - 1}
								<Breadcrumb.Page class="font-mono text-[11px]">{segment}</Breadcrumb.Page>
							{:else}
								<span class="font-mono text-[11px] text-muted-foreground">{segment}</span>
							{/if}
						</Breadcrumb.Item>
					{/each}
				</Breadcrumb.List>
			</Breadcrumb.Root>
		</div>
	{/if}

	<div class="host" data-readonly={readonly} bind:this={host}></div>

	{#if chrome}
		<div class="status">
			<div class="status-left">
				{#if errorCount || warningCount}
					<Button
						variant="ghost"
						size="sm"
						class="h-5 gap-1 px-1.5 text-[11px] {errorCount ? 'text-destructive' : 'text-warning'}"
						onclick={jumpToFirstIssue}
					>
						{#if errorCount}
							<CircleAlert size={11} />
							{errorCount} error{errorCount === 1 ? '' : 's'}
						{:else}
							<TriangleAlert size={11} />
							{warningCount} warning{warningCount === 1 ? '' : 's'}
						{/if}
					</Button>
				{:else}
					<span class="ok"><CircleCheck size={11} /> Valid</span>
				{/if}
				<span class="dim">Ln {cursorLine}, Col {cursorCol}</span>
			</div>
			<div class="status-right">
				<span class="dim">YAML · 2 spaces</span>
				<span class="hint">
					<Kbd.Group>
						<Kbd.Root>Ctrl</Kbd.Root>
						<Kbd.Root>Space</Kbd.Root>
					</Kbd.Group>
					complete
				</span>
				<span class="hint">
					<Kbd.Group>
						<Kbd.Root>{mod}</Kbd.Root>
						<Kbd.Root>F</Kbd.Root>
					</Kbd.Group>
					find
				</span>
				{#if !readonly}
					<span class="hint">
						<Kbd.Group>
							<Kbd.Root>{mod}</Kbd.Root>
							<Kbd.Root>S</Kbd.Root>
						</Kbd.Group>
						save
					</span>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.yaml-pane {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		overflow: hidden;
	}
	.host {
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}
	.host :global(.cm-editor) {
		height: 100%;
	}
	.crumbs {
		display: flex;
		align-items: center;
		flex-shrink: 0;
		height: 28px;
		padding: 0 12px;
		border-bottom: 1px solid var(--border);
		overflow: hidden;
		white-space: nowrap;
	}
	.status {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		flex-shrink: 0;
		height: 28px;
		padding: 0 8px 0 10px;
		border-top: 1px solid var(--border);
		font-size: 11px;
		color: var(--muted-foreground);
		overflow: hidden;
	}
	.status-left,
	.status-right {
		display: flex;
		align-items: center;
		gap: 12px;
		min-width: 0;
		white-space: nowrap;
	}
	.ok {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: var(--success);
	}
	.dim {
		font-variant-numeric: tabular-nums;
	}
	.hint {
		display: inline-flex;
		align-items: center;
		gap: 5px;
	}
	@media (max-width: 640px) {
		.hint {
			display: none;
		}
	}

	.host :global(.cm-yaml-num) {
		color: var(--chart-4);
	}
	.host :global(.cm-yaml-bool) {
		color: var(--chart-3);
	}
	.host :global(.cm-stage-key) {
		color: var(--primary);
		font-weight: 600;
	}
	.host :global(.cm-stage-dot) {
		display: block;
		width: 7px;
		height: 7px;
		margin: 9px 0 0 3px;
		border-radius: 999px;
		border: 1px solid var(--muted-foreground);
		cursor: pointer;
		opacity: 0.8;
	}
	.host[data-readonly='true'] :global(.cm-stage-dot) {
		cursor: default;
	}
	.host :global(.cm-stage-dot.on) {
		background: var(--primary);
		border-color: var(--primary);
		opacity: 1;
	}
	.host :global(.cm-fold-mark) {
		display: inline-block;
		width: 14px;
		text-align: center;
		font-size: 13px;
		line-height: 1.7;
		opacity: 0;
		transition: opacity 0.12s ease;
	}
	.host :global(.cm-gutters:hover .cm-fold-mark) {
		opacity: 0.7;
	}
	.host :global(.cm-foldPlaceholder) {
		background: var(--muted);
		border: none;
		color: var(--muted-foreground);
		border-radius: 4px;
		padding: 0 6px;
		margin: 0 4px;
	}
</style>
