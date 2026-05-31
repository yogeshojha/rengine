<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { EditorView, basicSetup } from 'codemirror';
	import { yaml } from '@codemirror/lang-yaml';
	import { oneDark } from '@codemirror/theme-one-dark';
	import { EditorState } from '@codemirror/state';
	import { lintGutter, linter, type Diagnostic } from '@codemirror/lint';
	import { AlertCircle } from 'lucide-svelte';

	interface YamlError {
		line: number;
		message: string;
	}

	interface Props {
		yamlContent: string;
		onChange?: (yaml: string) => void;
		errors?: YamlError[];
	}

	let { yamlContent, onChange, errors = [] }: Props = $props();

	let editorContainer: HTMLDivElement;
	let editorView: EditorView | null = null;
	let isDark = $state(false);

	// Detect dark mode
	$effect(() => {
		const mq = window.matchMedia('(prefers-color-scheme: dark)');
		isDark = mq.matches;
		const handler = (e: MediaQueryListEvent) => {
			isDark = e.matches;
			rebuildEditor();
		};
		mq.addEventListener('change', handler);
		return () => mq.removeEventListener('change', handler);
	});

	// External errors → CodeMirror diagnostics
	function buildLinter() {
		return linter(() => {
			return errors.map((err): Diagnostic => {
				const line = editorView?.state.doc.line(Math.max(1, err.line));
				return {
					from: line?.from ?? 0,
					to: line?.to ?? 0,
					severity: 'error',
					message: err.message
				};
			});
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

	// Sync external yamlContent changes into the editor (without losing cursor)
	$effect(() => {
		if (!editorView) return;
		const current = editorView.state.doc.toString();
		if (current !== yamlContent) {
			editorView.dispatch({
				changes: { from: 0, to: current.length, insert: yamlContent }
			});
		}
	});

	// Re-run lint when errors change
	$effect(() => {
		if (!editorView) return;
		// Touch errors to trigger reactivity, then rebuild linter
		const _ = errors.length;
		editorView.dispatch({}); // force lint re-run
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
		background: {isDark ? '#1a202c' : '#ffffff'};
	"
>
	<!-- Editor area -->
	<div
		style="
			flex: 1;
			overflow: hidden;
			border-radius: 8px;
			border: 1px solid {isDark ? '#2d3748' : '#e2e8f0'};
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
	{#if errors.length > 0}
		<div
			style="
				margin: 0 12px 12px;
				border-radius: 8px;
				border: 1px solid #fca5a5;
				background: #fef2f2;
				overflow: hidden;
			"
		>
			<div
				style="
					padding: 8px 12px;
					background: #fee2e2;
					border-bottom: 1px solid #fca5a5;
					display: flex;
					align-items: center;
					gap: 6px;
				"
			>
				<AlertCircle size={14} color="#dc2626" />
				<span style="font-size: 12px; font-weight: 600; color: #991b1b;">
					{errors.length} error{errors.length !== 1 ? 's' : ''}
				</span>
			</div>
			<div style="max-height: 140px; overflow-y: auto;">
				{#each errors as err}
					<div
						style="
							display: flex;
							align-items: flex-start;
							gap: 10px;
							padding: 6px 12px;
							border-bottom: 1px solid #fee2e2;
							font-size: 12px;
						"
					>
						<span
							style="
								flex-shrink: 0;
								font-family: monospace;
								font-weight: 600;
								color: #dc2626;
								background: #fee2e2;
								border: 1px solid #fca5a5;
								border-radius: 4px;
								padding: 1px 6px;
								white-space: nowrap;
							"
						>
							L{err.line}
						</span>
						<span style="color: #7f1d1d; line-height: 1.5; flex: 1;">{err.message}</span>
					</div>
				{/each}
			</div>
		</div>
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
		text-decoration: wavy underline #dc2626;
		text-decoration-skip-ink: none;
	}
</style>
