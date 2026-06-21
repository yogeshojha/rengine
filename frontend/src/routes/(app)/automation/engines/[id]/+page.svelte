<script lang="ts">
	import { untrack, onMount } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { page } from '$app/state';
	import { goto, replaceState, beforeNavigate } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { AlertTriangle, Loader2, X } from 'lucide-svelte';
	// @ts-expect-error no declaration file for js-yaml
	import jsyamlRaw from 'js-yaml';
	const jsyaml = jsyamlRaw as {
		dump: (obj: unknown, opts?: { indent?: number; lineWidth?: number; noRefs?: boolean }) => string;
		load: (str: string) => unknown;
	};

	import { Button } from '$lib/components/ui/button';
	import * as Empty from '$lib/components/ui/empty';
	import * as Sheet from '$lib/components/ui/sheet';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scanEnginesApi } from '$lib/api/scan-engines';
	import { IsMobile } from '$lib/hooks/is-mobile.svelte';

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

	let engineId = $derived(page.params.id);
	let isNew = $derived(engineId === 'new');

	let engine = $state<ScanEngine | null>(null);
	let editedEngine = $state<ScanEngine | null>(null);
	let isLoading = $state(false);
	let loadError = $state<string | null>(null);
	let isSaving = $state(false);
	let viewMode = $state<'canvas' | 'yaml'>(
		page.url.searchParams.get('view') === 'yaml' ? 'yaml' : 'canvas'
	);
	let selectedCapabilityId = $state<string | null>(page.url.searchParams.get('cap'));
	let previewMode = $state(false);
	let yamlContent = $state('');
	let yamlErrors = $state<{ line: number; message: string }[]>([]);
	let saveError = $state<string | null>(null);
	let addStepNonce = $state(0);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);
	let showLeaveDialog = $state(false);
	let pendingNav: (() => void) | null = $state(null);
	let allowNavigation = $state(false);
	const isMobile = new IsMobile(1024);

	let hasUnsavedChanges = $derived.by(() => {
		if (isNew) return editedEngine !== null;
		if (!engine || !editedEngine) return false;
		return JSON.stringify(engine) !== JSON.stringify(editedEngine);
	});

	let selectedCapability = $derived(
		selectedCapabilityId ? CAPABILITIES.find((c) => c.id === selectedCapabilityId) ?? null : null
	);

	let configPanelPhase = $derived(selectedCapability?.phase ?? null);

	let configPanelConfigPhase = $derived(
		selectedCapability ? configPhaseFor(selectedCapability.id, selectedCapability.phase) : null
	);

	let configPanelConfig = $derived.by(() => {
		if (!editedEngine || !configPanelConfigPhase) return null;
		return editedEngine[configPanelConfigPhase];
	});

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

	function handleConfigChange(updates: Record<string, unknown>) {
		if (!editedEngine || !configPanelConfigPhase) return;
		editedEngine = {
			...editedEngine,
			[configPanelConfigPhase]: { ...editedEngine[configPanelConfigPhase], ...updates }
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		} as any;
	}

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

	$effect(() => {
		const view = viewMode;
		const cap = selectedCapabilityId;
		untrack(() => {
			const params = new SvelteURLSearchParams(page.url.search);
			if (view === 'yaml') params.set('view', 'yaml');
			else params.delete('view');
			if (cap) params.set('cap', cap);
			else params.delete('cap');
			const qs = params.toString();
			const next = qs ? `?${qs}` : page.url.pathname;
			if (next !== page.url.pathname + page.url.search) replaceState(next, {});
		});
	});

	function initNewEngine(projectId: string) {
		const draft: ScanEngine = {
			id: '',
			project_id: projectId,
			name: '',
			created_by: '',
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
	}

	async function loadEngine(id: string, projectId: string) {
		isLoading = true;
		loadError = null;
		try {
			const cached = scanEnginesStore.engines.find((e) => e.id === id);
			if (cached) {
				// eslint-disable-next-line @typescript-eslint/no-explicit-any
				engine = cached as any as ScanEngine;
				editedEngine = JSON.parse(JSON.stringify(engine));
			}

			const fresh = await scanEnginesApi.get(id, projectId);
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			engine = fresh as any as ScanEngine;
			if (!hasUnsavedChanges) {
				editedEngine = JSON.parse(JSON.stringify(engine));
			}
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Failed to load engine';
		} finally {
			isLoading = false;
		}
	}

	function engineToYaml(eng: ScanEngine): string {
		const obj = {
			name: eng.name,
			intensity: eng.intensity,
			discovery: eng.discovery,
			expansion: eng.expansion,
			depth: eng.depth
		};
		return jsyaml.dump(obj, { indent: 2, lineWidth: -1, noRefs: true });
	}

	function yamlToEngine(yaml: string): ScanEngine | null {
		if (!editedEngine) return null;
		try {
			const parsed = jsyaml.load(yaml) as Record<string, unknown> | null;
			yamlErrors = [];
			if (!parsed || typeof parsed !== 'object') {
				yamlErrors = [{ line: 1, message: 'YAML must be a mapping of engine fields.' }];
				return null;
			}
			return {
				...editedEngine,
				name: (parsed.name as string) ?? editedEngine.name,
				intensity: (parsed.intensity as Intensity) ?? editedEngine.intensity,
				discovery: (parsed.discovery as ScanEngine['discovery']) ?? editedEngine.discovery,
				expansion: (parsed.expansion as ScanEngine['expansion']) ?? editedEngine.expansion,
				depth: (parsed.depth as ScanEngine['depth']) ?? editedEngine.depth
			};
		} catch (e) {
			const mark = (e as { mark?: { line?: number } })?.mark;
			const line = mark?.line != null ? mark.line + 1 : 1;
			const message = e instanceof Error ? e.message : 'Invalid YAML';
			yamlErrors = [{ line, message }];
			return null;
		}
	}

	function handleViewModeChange(mode: 'canvas' | 'yaml') {
		if (mode === 'yaml' && editedEngine) {
			yamlContent = engineToYaml(editedEngine);
			yamlErrors = [];
		} else if (mode === 'canvas' && viewMode === 'yaml') {
			const parsed = yamlToEngine(yamlContent);
			if (!parsed) {
				toast.error('YAML has errors — fix them before switching to Canvas');
				return;
			}
			editedEngine = parsed;
		}
		viewMode = mode;
	}

	function handleEngineChange(updated: ScanEngine) {
		if (!editedEngine) return;
		editedEngine = updated;
	}

	function handleNameChange(name: string) {
		if (!editedEngine) return;
		editedEngine = { ...editedEngine, name };
	}

	function handleIntensityChange(intensity: Intensity) {
		if (!editedEngine) return;
		editedEngine = { ...editedEngine, intensity };
	}

	async function handleSave() {
		if (!editedEngine || isSaving) return;
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('No active project');
			return;
		}
		if (!editedEngine.name.trim()) {
			saveError = 'Give the engine a name before saving.';
			toast.error(saveError);
			return;
		}

		isSaving = true;
		saveError = null;
		try {
			if (isNew) {
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
					allowNavigation = true;
					goto(`/automation/engines/${created.id}`, { replaceState: true });
				} else {
					saveError = scanEnginesStore.error ?? 'Failed to create engine';
					toast.error(saveError);
				}
			} else {
				const updated = await scanEnginesStore.updateEngine(engineId!, project.id, {
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

				if (updated) {
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
					engine = updated as any as ScanEngine;
					toast.success('Engine saved');
				} else {
					saveError = scanEnginesStore.error ?? 'Failed to save engine';
					toast.error(saveError);
				}
			}
		} finally {
			isSaving = false;
		}
	}

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

	async function handleDuplicate() {
		const project = projectsStore.activeProject;
		if (!project || !engineId) return;
		try {
			const dup = await scanEnginesStore.duplicateEngine(engineId, project.id);
			if (dup?.id) {
				toast.success(`Duplicated as "${dup.name}"`);
				allowNavigation = true;
				goto(`/automation/engines/${dup.id}`);
			} else {
				toast.error('Duplicate failed');
			}
		} catch {
			toast.error('Duplicate failed');
		}
	}

	function handleDelete() {
		if (!engineId) return;
		showDeleteDialog = true;
	}

	async function confirmDelete() {
		if (!engineId) return;
		isDeleting = true;
		try {
			const ok = await scanEnginesStore.deleteEngine(engineId);
			if (ok) {
				toast.success('Engine deleted');
				showDeleteDialog = false;
				allowNavigation = true;
				goto('/automation/engines');
			} else {
				toast.error('Delete failed');
			}
		} catch {
			toast.error('Delete failed');
		} finally {
			isDeleting = false;
		}
	}

	function handleYamlChange(yaml: string) {
		yamlContent = yaml;
		try {
			jsyaml.load(yaml);
			yamlErrors = [];
		} catch (e) {
			const mark = (e as { mark?: { line?: number } })?.mark;
			const line = mark?.line != null ? mark.line + 1 : 1;
			yamlErrors = [{ line, message: e instanceof Error ? e.message : 'Invalid YAML' }];
		}
	}

	function handleBack() {
		goto('/automation/engines');
	}

	function confirmLeave() {
		showLeaveDialog = false;
		const resume = pendingNav;
		pendingNav = null;
		allowNavigation = true;
		resume?.();
	}

	beforeNavigate((nav) => {
		if (allowNavigation) {
			allowNavigation = false;
			return;
		}
		if (!hasUnsavedChanges || pendingNav) return;
		nav.cancel();
		pendingNav = () => {
			allowNavigation = true;
			if (nav.to) goto(nav.to.url);
		};
		showLeaveDialog = true;
	});

	onMount(() => {
		const onBeforeUnload = (e: BeforeUnloadEvent) => {
			if (!hasUnsavedChanges) return;
			e.preventDefault();
			e.returnValue = '';
		};
		window.addEventListener('beforeunload', onBeforeUnload);
		return () => window.removeEventListener('beforeunload', onBeforeUnload);
	});
</script>

<div class="editor-shell">
	{#if isLoading && !engine}
		<div class="state-center">
			<Loader2 size={20} class="animate-spin text-muted-foreground" />
			<span class="text-sm text-muted-foreground">Loading engine…</span>
		</div>

	{:else if loadError}
		<Empty.Root class="flex-1">
			<Empty.Header>
				<Empty.Media class="size-[52px] rounded-xl bg-destructive/10">
					<AlertTriangle size={22} class="text-destructive" />
				</Empty.Media>
				<Empty.Title>Failed to load engine</Empty.Title>
				<Empty.Description>{loadError}</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button onclick={() => goto('/automation/engines')}>Back to Engines</Button>
			</Empty.Content>
		</Empty.Root>

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

		{#if saveError}
			<div class="save-error-bar" role="alert">
				<AlertTriangle size={13} class="shrink-0" />
				<span class="flex-1 truncate">Save failed — {saveError}</span>
				<Button
					variant="outline"
					size="sm"
					class="h-6 px-2 text-xs"
					disabled={isSaving}
					onclick={handleSave}
				>
					Retry
				</Button>
				<Button
					variant="ghost"
					size="icon-sm"
					class="h-6 w-6"
					aria-label="Dismiss"
					onclick={() => (saveError = null)}
				>
					<X size={13} />
				</Button>
			</div>
		{/if}

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
				<div class="config-col">
					<ConfigPanel
						capabilityId={selectedCapabilityId}
						phase={configPanelPhase}
						config={configPanelConfig}
						onChange={handleConfigChange}
						onClose={() => (selectedCapabilityId = null)}
					/>
				</div>
				<Sheet.Root
					open={isMobile.current && selectedCapabilityId !== null}
					onOpenChange={(o) => {
						if (!o) selectedCapabilityId = null;
					}}
				>
					<Sheet.Content
						side="right"
						class="config-sheet w-[calc(100%-2rem)] gap-0 p-0 sm:max-w-md lg:hidden"
					>
						<ConfigPanel
							capabilityId={selectedCapabilityId}
							phase={configPanelPhase}
							config={configPanelConfig}
							onChange={handleConfigChange}
							onClose={() => (selectedCapabilityId = null)}
						/>
					</Sheet.Content>
				</Sheet.Root>
			{:else}
				<div class="yaml-wrap">
					<YamlEditor {yamlContent} onChange={handleYamlChange} errors={yamlErrors} />
				</div>
			{/if}
		</div>
	{/if}
</div>

<!-- Delete confirmation -->
<DeleteConfirmationDialog
	bind:open={showDeleteDialog}
	title="Delete Engine"
	description="Are you sure you want to delete '{editedEngine?.name ?? 'this engine'}'? This action cannot be undone."
	{isDeleting}
	onOpenChange={(open) => (showDeleteDialog = open)}
	onConfirm={confirmDelete}
/>

<!-- Unsaved-changes guard -->
<AlertDialog.Root bind:open={showLeaveDialog}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Unsaved changes</AlertDialog.Title>
			<AlertDialog.Description>
				You have unsaved changes that will be lost. Leave anyway?
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel onclick={() => (pendingNav = null)}>Stay</AlertDialog.Cancel>
			<AlertDialog.Action onclick={confirmLeave}>Leave</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>

<style>
	.editor-shell {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		overflow: hidden;
		margin: -24px;
	}

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

	.save-error-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 5px 12px;
		background: color-mix(in oklch, var(--destructive) 8%, var(--card));
		border-bottom: 1px solid color-mix(in oklch, var(--destructive) 30%, var(--border));
		color: var(--destructive);
		font-size: 12px;
		font-weight: 500;
		flex-shrink: 0;
	}

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

	.config-col {
		display: none;
	}
	@media (min-width: 1024px) {
		.config-col {
			display: contents;
		}
	}

	:global(.config-sheet .config-panel) {
		width: 100%;
		border-left: none;
	}
</style>
