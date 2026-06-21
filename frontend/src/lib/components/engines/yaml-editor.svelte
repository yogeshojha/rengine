<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { EditorView, basicSetup } from 'codemirror';
	import { yaml } from '@codemirror/lang-yaml';
	import { oneDark } from '@codemirror/theme-one-dark';
	import { EditorState } from '@codemirror/state';
	import { lintGutter, linter, type Diagnostic } from '@codemirror/lint';
	import { syntaxTree } from '@codemirror/language';
	import { AlertCircle } from 'lucide-svelte';
	import { mode } from 'mode-watcher';
	import * as Alert from '$lib/components/ui/alert';
	import { ScrollArea } from '$lib/components/ui/scroll-area';

	interface YamlError {
		line: number;
		message: string;
	}

	interface Props {
		yamlContent: string;
		onChange?: (yaml: string) => void;
		errors?: YamlError[];
		onValidityChange?: (valid: boolean) => void;
	}

	let { yamlContent, onChange, errors = [], onValidityChange }: Props = $props();

	let editorContainer: HTMLDivElement;
	let editorView: EditorView | null = null;
	let isDark = $derived(mode.current === 'dark');
	let yamlErrors = $state<YamlError[]>([]);
	let allErrors = $derived([...yamlErrors, ...errors]);

	$effect(() => {
		void isDark;
		if (editorView) rebuildEditor();
	});

	function buildLinter() {
		return linter((view): Diagnostic[] => {
			const diagnostics: Diagnostic[] = [];
			const found: YamlError[] = [];

			syntaxTree(view.state)
				.cursor()
				.iterate((node) => {
					if (!node.type.isError) return;
					const from = node.from;
					const to =
						node.to > node.from ? node.to : Math.min(node.from + 1, view.state.doc.length);
					const lineNo = view.state.doc.lineAt(from).number;
					const message = 'Invalid YAML syntax';
					diagnostics.push({ from, to, severity: 'error', message });
					found.push({ line: lineNo, message });
				});

			for (const err of errors) {
				const line = view.state.doc.line(Math.max(1, err.line));
				diagnostics.push({ from: line.from, to: line.to, severity: 'error', message: err.message });
			}

			yamlErrors = found;
			onValidityChange?.(found.length === 0);
			return diagnostics;
		});
	}

	function getExtensions() {
		const exts = [
			basicSetup,
			yaml(),
			lintGutter(),
			buildLinter(),
			EditorView.updateListener.of((update) => {
				if (update.docChanged) {
					onChange?.(update.state.doc.toString());
				}
			}),
			EditorView.theme({
				'&': {
					fontSize: '13px',
					fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
					height: '100%'
				},
				'.cm-scroller': {
					overflow: 'auto',
					lineHeight: '1.6'
				},
				'.cm-content': {
					caretColor: isDark ? '#a5b4fc' : '#4f46e5'
				},
				'.cm-focused': {
					outline: 'none'
				},
				'.cm-gutters': {
					borderRight: isDark ? '1px solid #2d3748' : '1px solid #e2e8f0',
					background: isDark ? '#1a202c' : '#f8fafc',
					color: isDark ? '#4a5568' : '#94a3b8'
				},
				'.cm-activeLineGutter': {
					background: isDark ? '#2d3748' : '#eff6ff'
				},
				'.cm-activeLine': {
					background: isDark ? 'rgba(99,102,241,0.08)' : 'rgba(79,70,229,0.04)'
				}
			}),
			...(isDark ? [oneDark] : [])
		];
		return exts;
	}

	function rebuildEditor() {
		if (!editorContainer) return;
		const doc = editorView?.state.doc.toString() ?? yamlContent;
		editorView?.destroy();
		editorView = new EditorView({
			state: EditorState.create({
				doc,
				extensions: getExtensions()
			}),
			parent: editorContainer
		});
	}

	onMount(() => {
		editorView = new EditorView({
			state: EditorState.create({
				doc: yamlContent,
				extensions: getExtensions()
			}),
			parent: editorContainer
		});
	});

	$effect(() => {
		if (!editorView) return;
		const current = editorView.state.doc.toString();
		if (current !== yamlContent) {
			editorView.dispatch({
				changes: { from: 0, to: current.length, insert: yamlContent }
			});
		}
	});

	$effect(() => {
		if (!editorView) return;
		void errors.length;
		editorView.dispatch({});
	});

	onDestroy(() => {
		editorView?.destroy();
	});
</script>

<div
	style="
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--card);
	"
>
	<!-- Editor area -->
	<div
		style="
			flex: 1;
			overflow: hidden;
			border-radius: 8px;
			border: 1px solid var(--border);
			margin: 12px;
			box-shadow: 0 1px 4px rgba(0,0,0,0.06);
		"
	>
		<div
			bind:this={editorContainer}
			style="height: 100%; overflow: auto;"
		></div>
	</div>

	<!-- Error list -->
	{#if allErrors.length > 0}
		<Alert.Root variant="destructive" class="mx-3 mb-3 block w-auto overflow-hidden p-0">
			<div class="flex items-center gap-1.5 border-b border-destructive/40 bg-destructive/10 px-3 py-2">
				<AlertCircle class="size-3.5 text-destructive" />
				<span class="text-xs font-semibold text-destructive">
					{allErrors.length} error{allErrors.length !== 1 ? 's' : ''}
				</span>
			</div>
			<ScrollArea class="h-[140px]">
				{#each allErrors as err, i (i)}
					<div
						class="flex items-start gap-2.5 border-b border-destructive/20 px-3 py-1.5 text-xs"
					>
						<span
							class="shrink-0 whitespace-nowrap rounded border border-destructive/40 bg-destructive/10 px-1.5 py-px font-mono font-semibold text-destructive"
						>
							L{err.line}
						</span>
						<span class="flex-1 leading-normal text-destructive/90">{err.message}</span>
					</div>
				{/each}
			</ScrollArea>
		</Alert.Root>
	{/if}
</div>

<style>
	:global(.cm-editor) {
		height: 100%;
	}
	:global(.cm-editor.cm-focused) {
		outline: none;
	}
	:global(.cm-scroller) {
		font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace !important;
	}
	:global(.cm-diagnostic-error) {
		text-decoration: wavy underline var(--destructive);
		text-decoration-skip-ink: none;
	}
</style>
