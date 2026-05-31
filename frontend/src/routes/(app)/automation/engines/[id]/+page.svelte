<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { AlertTriangle, Loader2 } from 'lucide-svelte';

	import { Button } from '$lib/components/ui/button';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scanEnginesApi } from '$lib/api/scan-engines';

	import EngineCanvas from '$lib/components/engines/engine-canvas.svelte';
	import EngineTopbar from '$lib/components/engines/engine-topbar.svelte';
	import YamlEditor from '$lib/components/engines/yaml-editor.svelte';
	import ConfigPanel from '$lib/components/engines/config-panel.svelte';

	import type { ScanEngine, Intensity } from '$lib/types/engine';
	import {
		DEFAULT_DISCOVERY_CONFIG,
		DEFAULT_EXPANSION_CONFIG,
		DEFAULT_DEPTH_CONFIG
	} from '$lib/types/engine';
	import { CAPABILITIES, getActiveCapabilities, configPhaseFor } from '$lib/types/capabilities';

	// ── Route param ────────────────────────────────────────────────────────────
	let engineId = $derived(page.params.id);
	let isNew = $derived(engineId === 'new');

	// ── Page state ─────────────────────────────────────────────────────────────
	let engine = $state<ScanEngine | null>(null);
	let editedEngine = $state<ScanEngine | null>(null);
	let isLoading = $state(false);
	let loadError = $state<string | null>(null);
	let isSaving = $state(false);
	let viewMode = $state<'canvas' | 'yaml'>('canvas');
	let selectedCapabilityId = $state<string | null>(null);
	let previewMode = $state(false);
	let yamlContent = $state('');
	// nonce bumped by topbar "+ Add Step" to open the canvas all-phases palette
	let addStepNonce = $state(0);

	// ── Derived ────────────────────────────────────────────────────────────────
	let hasUnsavedChanges = $derived.by(() => {
		if (isNew) return editedEngine !== null;
		if (!engine || !editedEngine) return false;
		return JSON.stringify(engine) !== JSON.stringify(editedEngine);
	});

	// Derive phase and config from selectedCapabilityId for ConfigPanel
	let selectedCapability = $derived(
		selectedCapabilityId ? CAPABILITIES.find((c) => c.id === selectedCapabilityId) ?? null : null
	);

	// Node phase — drives the panel header accent only.
	let configPanelPhase = $derived(selectedCapability?.phase ?? null);

	// Phase-config object that actually holds the selected capability's fields.
	// Differs from node phase for takeover-dns (expansion) and url-discovery/dir-fuzz/param-vhost (depth).
	let configPanelConfigPhase = $derived(
		selectedCapability ? configPhaseFor(selectedCapability.id, selectedCapability.phase) : null
	);

	let configPanelConfig = $derived.by(() => {
		if (!editedEngine || !configPanelConfigPhase) return null;
		return editedEngine[configPanelConfigPhase];
	});

	// Topbar summary: tool count + rough duration estimate across active capabilities
	let toolCount = $derived.by(() => {
		if (!editedEngine) return 0;
		const tools: string[] = [];
		for (const cap of getActiveCapabilities(editedEngine)) {
			for (const t of cap.tools) if (!tools.includes(t)) tools.push(t);
		}
		return tools.length;
	});

	let estDuration = $derived.by(() => {
		if (!editedEngine) return '0m';
		const active = getActiveCapabilities(editedEngine);
		const heavy = active.filter((c) => c.phase === 'expansion' || c.phase === 'depth').length;
		const mins = 2 + heavy * 4;
		return `${mins}m`;
	});

	// ── Config panel change handler ───────────────────────────────────────────
	function handleConfigChange(updates: Record<string, unknown>) {
		if (!editedEngine || !configPanelConfigPhase) return;
		editedEngine = {
			...editedEngine,
			[configPanelConfigPhase]: { ...editedEngine[configPanelConfigPhase], ...updates }
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		} as any;
	}

	// ── Load / init engine ────────────────────────────────────────────────────
	$effect(() => {
		const project = projectsStore.activeProject;
		const id = engineId;
		if (!project) return;

		untrack(() => {
			if (id === 'new') {
				initNewEngine(project.id);
			} else if (id) {
				loadEngine(id, project.id);
			}
		});
	});

	function initNewEngine(projectId: string) {
		// Build a local draft — no API call until Save is clicked
		const draft: ScanEngine = {
			id: '',
			project_id: projectId,
			created_by: '',
			name: 'New Scan Engine',
			description: null,
			intensity: 'normal',
			global_threads: 30,
			global_http_crawl: true,
			global_headers: [],
			discovery: { ...DEFAULT_DISCOVERY_CONFIG },
			expansion: { ...DEFAULT_EXPANSION_CONFIG },
			depth: { ...DEFAULT_DEPTH_CONFIG },
			created_at: '',
			updated_at: '',
			last_used_at: null
		};
		editedEngine = draft;
		// engine stays null — used to detect "unsaved" state
	}

	async function loadEngine(id: string, projectId: string) {
		isLoading = true;
		loadError = null;
		try {
			// Try cache first
			const cached = scanEnginesStore.engines.find((e) => e.id === id);
			if (cached) {
				// eslint-disable-next-line @typescript-eslint/no-explicit-any
				engine = cached as any as ScanEngine;
				// JSON round-trip to strip Svelte reactive proxy before deep-copy
				editedEngine = JSON.parse(JSON.stringify(engine));
			}

			// Always fetch fresh from API
			const fresh = await scanEnginesApi.get(id, projectId);
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			engine = fresh as any as ScanEngine;
			// Only update editedEngine from API if no unsaved local changes
			if (!hasUnsavedChanges) {
				editedEngine = JSON.parse(JSON.stringify(engine));
			}
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Failed to load engine';
		} finally {
			isLoading = false;
		}
	}

	// ── YAML generation ───────────────────────────────────────────────────────
	function engineToYaml(eng: ScanEngine): string {
		const obj = {
			name: eng.name,
			intensity: eng.intensity,
			discovery: eng.discovery,
			expansion: eng.expansion,
			depth: eng.depth
		};
		// Simple YAML-like serialization (no js-yaml dependency)
		return JSON.stringify(obj, null, 2)
			.replace(/"([a-zA-Z_][a-zA-Z0-9_]*)"\s*:/g, '$1:')
			.replace(/"/g, "'");
	}

	function yamlToEngine(yaml: string): ScanEngine | null {
		try {
			// Reverse our simple serialization: restore quotes around values
			const jsonStr = yaml
				.replace(/([a-zA-Z_][a-zA-Z0-9_]*):/g, '"$1":')
				.replace(/'/g, '"');
			const parsed = JSON.parse(jsonStr);
			if (!editedEngine) return null;
			return {
				...editedEngine,
				name: parsed.name ?? editedEngine.name,
				intensity: parsed.intensity ?? editedEngine.intensity,
				discovery: parsed.discovery ?? editedEngine.discovery,
				expansion: parsed.expansion ?? editedEngine.expansion,
				depth: parsed.depth ?? editedEngine.depth
			};
		} catch {
			return null;
		}
	}

	// ── View mode switch ──────────────────────────────────────────────────────
	function handleViewModeChange(mode: 'canvas' | 'yaml') {
		if (mode === 'yaml' && editedEngine) {
			yamlContent = engineToYaml(editedEngine);
		} else if (mode === 'canvas' && viewMode === 'yaml') {
			const parsed = yamlToEngine(yamlContent);
			if (parsed) editedEngine = parsed;
		}
		viewMode = mode;
	}

	// ── Canvas engine change — receives full updated ScanEngine ──────────────
	function handleEngineChange(updated: ScanEngine) {
		if (!editedEngine) return;
		editedEngine = updated;
	}

	// ── Name / intensity edits ────────────────────────────────────────────────
	function handleNameChange(name: string) {
		if (!editedEngine) return;
		editedEngine = { ...editedEngine, name };
	}

	function handleIntensityChange(intensity: Intensity) {
		if (!editedEngine) return;
		editedEngine = { ...editedEngine, intensity };
	}

	// ── Save ──────────────────────────────────────────────────────────────────
	async function handleSave() {
		if (!editedEngine || isSaving) return;
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('No active project');
			return;
		}

		isSaving = true;
		try {
			if (isNew) {
				// First save for a new engine — POST to create
				const created = await scanEnginesStore.createEngine(project.id, {
					name: editedEngine.name,
					intensity: editedEngine.intensity,
					description: editedEngine.description,
					global_threads: editedEngine.global_threads,
					global_http_crawl: editedEngine.global_http_crawl,
					global_headers: editedEngine.global_headers,
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
					discovery: editedEngine.discovery as any,
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
					expansion: editedEngine.expansion as any,
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
					depth: editedEngine.depth as any
				});
				if (created) {
					toast.success('Engine created');
					// Replace the /new URL with the real ID (no history entry)
					goto(`/automation/engines/${created.id}`, { replaceState: true });
				} else {
					toast.error(scanEnginesStore.error ?? 'Failed to create engine');
				}
			} else {
				// Existing engine — PATCH
				const updated = await scanEnginesStore.updateEngine(engineId!, project.id, {
					name: editedEngine.name,
					intensity: editedEngine.intensity,
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
					discovery: editedEngine.discovery as any,
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
					expansion: editedEngine.expansion as any,
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
					depth: editedEngine.depth as any
				});

				if (updated) {
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
					engine = updated as any as ScanEngine;
					toast.success('Engine saved');
				} else {
					toast.error(scanEnginesStore.error ?? 'Failed to save engine');
				}
			}
		} finally {
			isSaving = false;
		}
	}

	// ── Export YAML ───────────────────────────────────────────────────────────
	async function handleExportYaml() {
		const project = projectsStore.activeProject;
		if (!project || !engineId) return;
		try {
			const yaml = await scanEnginesStore.exportYaml(engineId, project.id);
			if (yaml) {
				const blob = new Blob([yaml], { type: 'text/yaml' });
				const url = URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = `${editedEngine?.name ?? 'engine'}.yaml`;
				a.click();
				URL.revokeObjectURL(url);
				toast.success('YAML exported');
			} else {
				toast.error('Export failed');
			}
		} catch {
			toast.error('Export failed');
		}
	}

	// ── Duplicate ─────────────────────────────────────────────────────────────
	async function handleDuplicate() {
		const project = projectsStore.activeProject;
		if (!project || !engineId) return;
		try {
			const dup = await scanEnginesStore.duplicateEngine(engineId, project.id);
			if (dup?.id) {
				toast.success(`Duplicated as "${dup.name}"`);
				goto(`/automation/engines/${dup.id}`);
			} else {
				toast.error('Duplicate failed');
			}
		} catch {
			toast.error('Duplicate failed');
		}
	}

	// ── Delete ────────────────────────────────────────────────────────────────
	async function handleDelete() {
		if (!engineId) return;
		const confirmed = window.confirm(
			`Delete "${editedEngine?.name ?? 'this engine'}"? This cannot be undone.`
		);
		if (!confirmed) return;

		try {
			const ok = await scanEnginesStore.deleteEngine(engineId);
			if (ok) {
				toast.success('Engine deleted');
				goto('/automation/engines');
			} else {
				toast.error('Delete failed');
			}
		} catch {
			toast.error('Delete failed');
		}
	}

	// ── YAML editor change ────────────────────────────────────────────────────
	function handleYamlChange(yaml: string) {
		yamlContent = yaml;
	}

	// ── Back navigation ───────────────────────────────────────────────────────
	function handleBack() {
		if (hasUnsavedChanges) {
			const leave = window.confirm('You have unsaved changes. Leave anyway?');
			if (!leave) return;
		}
		goto('/automation/engines');
	}
</script>

<!--
	Full-screen editor layout.
	The parent layout wraps this in the sidebar/topbar shell.
	We use flex-col + overflow-hidden to fill available space.
-->
<div class="editor-shell">
	{#if isLoading && !engine}
		<div class="state-center">
			<Loader2 size={20} class="animate-spin text-muted-foreground" />
			<span class="text-sm text-muted-foreground">Loading engine…</span>
		</div>

	{:else if loadError}
		<div class="state-center state-error">
			<div class="error-icon">
				<AlertTriangle size={22} class="text-destructive" />
			</div>
			<div>
				<p class="error-title">Failed to load engine</p>
				<p class="error-msg">{loadError}</p>
			</div>
			<Button onclick={() => goto('/automation/engines')}>Back to Engines</Button>
		</div>

	{:else if editedEngine}
		<EngineTopbar
			engine={editedEngine}
			{isSaving}
			{viewMode}
			{previewMode}
			{toolCount}
			{estDuration}
			{hasUnsavedChanges}
			onSave={handleSave}
			onDuplicate={isNew ? undefined : handleDuplicate}
			onDelete={isNew ? undefined : handleDelete}
			onExportYaml={isNew ? undefined : handleExportYaml}
			onViewModeChange={handleViewModeChange}
			onNameChange={handleNameChange}
			onIntensityChange={handleIntensityChange}
			onTogglePreview={() => (previewMode = !previewMode)}
			onAddStep={() => (addStepNonce += 1)}
			onBack={handleBack}
		/>

		<!-- Unsaved / new indicator -->
		{#if hasUnsavedChanges}
			<div class="unsaved-bar">
				<span class="unsaved-dot"></span>
				{#if isNew}
					New engine — click Save Engine to create
				{:else}
					Unsaved changes — click Save Engine to apply
				{/if}
			</div>
		{/if}

		<!-- Main content: canvas or YAML -->
		<div class="editor-content">
			{#if viewMode === 'canvas'}
				<EngineCanvas
					engine={editedEngine}
					{selectedCapabilityId}
					{previewMode}
					requestAddOpen={addStepNonce}
					onCapabilitySelected={(id) => (selectedCapabilityId = id)}
					onEngineChange={handleEngineChange}
				/>
				<ConfigPanel
					capabilityId={selectedCapabilityId}
					phase={configPanelPhase}
					config={configPanelConfig}
					onChange={handleConfigChange}
					onClose={() => (selectedCapabilityId = null)}
				/>
			{:else}
				<div class="yaml-wrap">
					<YamlEditor {yamlContent} onChange={handleYamlChange} />
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.editor-shell {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		overflow: hidden;
		margin: -24px;
	}

	/* Centered state screens (loading / error) */
	.state-center {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 14px;
		text-align: center;
		padding: 40px;
	}

	.error-icon {
		width: 52px;
		height: 52px;
		border-radius: 12px;
		background: oklch(0.95 0.05 25);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	:global(.dark) .error-icon {
		background: oklch(0.22 0.05 25);
	}

	.error-title {
		font-size: 15px;
		font-weight: 700;
		color: var(--foreground);
		margin: 0 0 5px;
	}

	.error-msg {
		font-size: 13px;
		color: var(--muted-foreground);
		margin: 0;
	}

	/* Unsaved-changes bar — subtle monochrome notice strip */
	.unsaved-bar {
		height: 26px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--muted);
		border-bottom: 1px solid var(--border);
		font-size: 11px;
		color: var(--muted-foreground);
		font-weight: 500;
		gap: 6px;
		flex-shrink: 0;
	}

	.unsaved-dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: var(--muted-foreground);
		flex-shrink: 0;
	}

	/* Editor layout */
	.editor-content {
		flex: 1;
		min-height: 0;
		display: flex;
		overflow: hidden;
	}

	.yaml-wrap {
		flex: 1;
		min-width: 0;
		overflow: hidden;
		height: 100%;
	}
</style>
