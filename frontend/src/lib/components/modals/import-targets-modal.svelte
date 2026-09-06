<script lang="ts">
	import FileText from '@lucide/svelte/icons/file-text';
	import Code from '@lucide/svelte/icons/code';
	import List from '@lucide/svelte/icons/list';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import Eye from '@lucide/svelte/icons/eye';
	import Rocket from '@lucide/svelte/icons/rocket';
	import Upload from '@lucide/svelte/icons/upload';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Button } from '$lib/components/ui/button';
	import { Progress } from '$lib/components/ui/progress';
	import { Label } from '$lib/components/ui/label';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Tabs from '$lib/components/ui/tabs';
	import { Separator } from '$lib/components/ui/separator';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import FileUpload from '$lib/components/targets/file-upload.svelte';
	import ImportPreview from '$lib/components/targets/import-preview.svelte';
	import ImportResults from '$lib/components/targets/import-results.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { toast } from 'svelte-sonner';
	import ImportHelpText from '$lib/components/targets/import-helper.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import QuickScanFields from '$lib/components/scans/quick-scan-fields.svelte';
	import { MAX_SCAN_BATCH } from '$lib/types/scan';
	import { ROUTES } from '$lib/config/routes';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { SELECT_NONE } from '$lib/constants';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import {
		quickScanPlan,
		rememberQuickScanChoice,
		type QuickScanSelection
	} from '$lib/utilities/quick-scan';
	import { goto } from '$app/navigation';
	import type {
		TargetImportItem,
		TargetPreviewItem,
		TargetBulkCreateResponse
	} from '$lib/types/target';

	interface Props {
		open: boolean;
	}

	let { open = $bindable() }: Props = $props();

	type ImportMode = 'input' | 'preview' | 'results';
	type ImportMethod = 'manual' | 'json' | 'csv';

	let mode = $state<ImportMode>('input');
	let activeTab = $state<ImportMethod>('manual');

	let manualText = $state('');
	let manualFile = $state<File | null>(null);
	let manualMode = $state<'text' | 'file'>('text');

	let jsonText = $state('');
	let jsonFile = $state<File | null>(null);
	let jsonMode = $state<'text' | 'file'>('text');

	let csvFile = $state<File | null>(null);

	let previewItems = $state<TargetPreviewItem[]>([]);

	let importResults = $state<TargetBulkCreateResponse | null>(null);

	let isProcessing = $state(false);
	let isImporting = $state(false);

	let showLaunch = $state(false);
	let launchIds = $state<string[] | undefined>(undefined);

	let scanAfterImport = $state(false);
	let selection = $state<QuickScanSelection | null>(null);
	let contextId = $state(SELECT_NONE);
	let scanArmed = $state(false);
	let scanPending = $state(false);
	let queuedScans = $state(0);

	let validateDone = $state(0);
	let validateTotal = $state(0);
	let validatePct = $derived(validateTotal > 0 ? (validateDone / validateTotal) * 100 : 0);

	let busy = $derived(isProcessing || isImporting);

	function resetForm() {
		manualText = '';
		manualFile = null;
		manualMode = 'text';
		jsonText = '';
		jsonFile = null;
		jsonMode = 'text';
		csvFile = null;
		previewItems = [];
	}

	function resetModal() {
		mode = 'input';
		resetForm();
		importResults = null;
		isProcessing = false;
		isImporting = false;
		validateDone = 0;
		validateTotal = 0;
		queuedScans = 0;
	}

	function handleOpenChange(isOpen: boolean) {
		if (!isOpen) {
			resetModal();
		}
		open = isOpen;
	}

	function parseManualInput(text: string) {
		return text
			.split('\n')
			.map((line) => line.trim())
			.filter((line) => line.length > 0)
			.map((target_value) => ({ target_value }));
	}

	function parseJsonInput(text: string): TargetImportItem[] {
		try {
			const parsed = JSON.parse(text);

			if (Array.isArray(parsed)) {
				return parsed.map((item) =>
					typeof item === 'string' ? { target_value: item } : (item as TargetImportItem)
				);
			}

			if (parsed.targets && Array.isArray(parsed.targets)) {
				return parsed.targets as TargetImportItem[];
			}

			throw new Error('Invalid JSON format');
		} catch {
			throw new Error(
				'Invalid JSON format. Expected array of targets or object with "targets" array.'
			);
		}
	}

	async function parseCsvFile(file: File): Promise<TargetImportItem[]> {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();

			reader.onload = (e) => {
				try {
					const text = e.target?.result as string;
					const lines = text.split('\n').filter((line) => line.trim());

					if (lines.length === 0) {
						reject(new Error('CSV file is empty'));
						return;
					}

					const firstLine = lines[0].toLowerCase();
					const hasHeaders =
						firstLine.includes('target') ||
						firstLine.includes('domain') ||
						firstLine.includes('value') ||
						firstLine.includes('ip');

					const dataLines = hasHeaders ? lines.slice(1) : lines;

					const items = dataLines.map((line) => {
						const parts = line.split(',').map((p) => p.trim().replace(/^["']|["']$/g, ''));

						const item: TargetImportItem = {
							target_value: parts[0]
						};

						if (parts[1]) {
							const tags = parts[1]
								.split(',')
								.map((t) => t.trim())
								.filter(Boolean);
							if (tags.length > 0) item.tags = tags;
						}

						if (parts[2]) {
							const orgs = parts[2]
								.split(',')
								.map((o) => o.trim())
								.filter(Boolean);
							if (orgs.length > 0) item.organizations = orgs;
						}

						if (parts[3]) {
							item.display_name = parts[3];
						}

						return item;
					});

					resolve(items.filter((item) => item.target_value));
				} catch {
					reject(new Error('CSV file could not be read'));
				}
			};

			reader.onerror = () => reject(new Error('File could not be read'));
			reader.readAsText(file);
		});
	}

	async function readTextFile(file: File): Promise<string> {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = (e) => resolve(e.target?.result as string);
			reader.onerror = () => reject(new Error('File could not be read'));
			reader.readAsText(file);
		});
	}

	async function getInputItems(): Promise<TargetImportItem[]> {
		let items: TargetImportItem[] = [];

		if (activeTab === 'manual') {
			const source = manualMode === 'text' ? manualText : manualFile;
			if (!source) {
				toast.error('Enter at least one target, or upload a file');
				return [];
			}

			if (manualMode === 'text') {
				items = parseManualInput(manualText);
			} else if (manualFile) {
				const text = await readTextFile(manualFile);
				items = parseManualInput(text);
			}
		} else if (activeTab === 'json') {
			const source = jsonMode === 'text' ? jsonText : jsonFile;
			if (!source) {
				toast.error('Enter JSON, or upload a file');
				return [];
			}

			if (jsonMode === 'text') {
				items = parseJsonInput(jsonText);
			} else if (jsonFile) {
				const text = await readTextFile(jsonFile);
				items = parseJsonInput(text);
			}
		} else if (activeTab === 'csv') {
			if (!csvFile) {
				toast.error('Select a CSV file');
				return [];
			}
			items = await parseCsvFile(csvFile);
		}

		if (items.length === 0) {
			toast.error('No valid targets found');
			return [];
		}

		if (items.length > 500) {
			toast.error('Maximum 500 targets allowed per import');
			return [];
		}

		return items;
	}

	async function validateItem(item: TargetImportItem): Promise<TargetPreviewItem> {
		try {
			const result = await targetsApi.validate({ target_value: item.target_value });
			return {
				...item,
				target_type: result.valid ? result.target_type : null,
				error: result.valid ? undefined : result.error || 'Invalid target'
			};
		} catch {
			return { ...item, error: 'Validation failed' };
		}
	}

	async function handlePreview() {
		isProcessing = true;
		validateDone = 0;
		validateTotal = 0;

		try {
			const items = await getInputItems();
			if (items.length === 0) {
				isProcessing = false;
				return;
			}

			validateTotal = items.length;
			const CHUNK = 10;
			const validated: TargetPreviewItem[] = [];

			for (let i = 0; i < items.length; i += CHUNK) {
				const chunk = items.slice(i, i + CHUNK);
				const results = await Promise.all(chunk.map(validateItem));
				validated.push(...results);
				validateDone = validated.length;
			}

			previewItems = validated;
			mode = 'preview';
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Input could not be processed');
		} finally {
			isProcessing = false;
			validateDone = 0;
			validateTotal = 0;
		}
	}

	async function handleDirectImport() {
		isImporting = true;

		try {
			const items = await getInputItems();
			if (items.length === 0) {
				isImporting = false;
				return;
			}

			await executeImport(items);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Import failed');
			isImporting = false;
		}
	}

	async function handleImportFromPreview() {
		isImporting = true;

		try {
			const validItems = previewItems.filter((item) => !item.error);
			await executeImport(validItems);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Import failed');
			isImporting = false;
		}
	}

	async function executeImport(items: TargetImportItem[]) {
		const projectSlug = projectsStore.activeProject?.slug;
		if (!projectSlug) return;

		const wantsScan = scanArmed;
		queuedScans = 0;

		try {
			let response;

			if (activeTab === 'csv' && csvFile) {
				response = await targetsApi.importCsv(projectSlug, csvFile);
			} else {
				const targets = items.map((item) => ({
					target_value: item.target_value,
					tags: item.tags,
					organizations: item.organizations,
					display_name: item.display_name
				}));

				response = await targetsApi.importJson({
					project_slug: projectSlug,
					targets
				});
			}

			importResults = response;
			mode = 'results';

			await targetsStore.refresh();

			if (response.imported > 0) {
				toast.success(`Imported ${response.imported} target${response.imported !== 1 ? 's' : ''}`);
				if (wantsScan) await launchImported();
			} else if (wantsScan) {
				toast.warning('No new targets were imported. No scan was queued.');
			}

			if (response.failed > 0) {
				toast.warning(
					`${response.failed} target${response.failed !== 1 ? 's' : ''} failed to import`
				);
			}
		} finally {
			isImporting = false;
		}
	}

	function handleImportMore() {
		resetForm();
		mode = 'input';
	}

	let importedIds = $derived(
		(importResults?.results ?? [])
			.filter((r) => r.success && r.target_id)
			.map((r) => r.target_id as string)
	);

	function scanImported() {
		const ids = importedIds.slice(0, MAX_SCAN_BATCH);
		if (ids.length === 0) return;
		launchIds = ids;
		resetModal();
		open = false;
		showLaunch = true;
	}

	async function launchImported() {
		const project = projectsStore.activeProject;
		const ids = importedIds.slice(0, MAX_SCAN_BATCH);
		if (!project || ids.length === 0) return;

		if (!selection) return;
		const presets = engineCatalogStore.presets;
		const scans = await scansStore.launchScans(project.id, {
			...quickScanPlan(selection, presets),
			context_id: contextId === SELECT_NONE ? null : contextId,
			target_ids: ids
		});

		if (scans && scans.length > 0) {
			rememberQuickScanChoice(selection, contextId === SELECT_NONE ? null : contextId, presets);
			queuedScans = scans.length;
			toast.success(`${scans.length} scan${scans.length !== 1 ? 's' : ''} queued`);
		} else {
			toast.error(
				scansStore.error
					? `Targets imported, but the scans could not be queued. ${scansStore.error}`
					: 'Targets imported, but the scans could not be queued.'
			);
		}
	}

	function viewScans() {
		resetModal();
		open = false;
		goto(ROUTES.scans);
	}

	let hasInput = $derived(
		(activeTab === 'manual' && (manualText.trim().length > 0 || manualFile !== null)) ||
			(activeTab === 'json' && (jsonText.trim().length > 0 || jsonFile !== null)) ||
			(activeTab === 'csv' && csvFile !== null)
	);

	let canImport = $derived(
		mode === 'preview' && previewItems.length > 0 && previewItems.some((item) => !item.error)
	);
</script>

<Dialog.Root {open} onOpenChange={handleOpenChange}>
	<Dialog.Content
		class="grid max-h-[85vh] grid-rows-[auto_auto_minmax(0,1fr)] gap-0 overflow-hidden p-0 sm:max-w-[700px]"
		onInteractOutside={(e) => {
			if (busy) e.preventDefault();
		}}
		onEscapeKeydown={(e) => {
			if (busy) e.preventDefault();
		}}
	>
		<Dialog.Header class="p-6 pb-4">
			<Dialog.Title>Import targets</Dialog.Title>
			<Dialog.Description>
				{#if mode === 'input'}
					Paste a list, upload a file, or pull from a connected source
				{:else if mode === 'preview'}
					Review targets before importing
				{:else}
					Import complete
				{/if}
			</Dialog.Description>
		</Dialog.Header>

		<Separator />

		<ScrollArea class="min-h-0">
			{#if mode === 'input'}
				<Tabs.Root bind:value={activeTab} class="w-full">
					<div class="px-6 pt-4">
						<Tabs.List class="grid w-full grid-cols-3">
							<Tabs.Trigger value="manual" class="gap-2">
								<List class="h-4 w-4" />
								Manual
							</Tabs.Trigger>
							<Tabs.Trigger value="json" class="gap-2">
								<Code class="h-4 w-4" />
								JSON
							</Tabs.Trigger>
							<Tabs.Trigger value="csv" class="gap-2">
								<FileText class="h-4 w-4" />
								CSV
							</Tabs.Trigger>
						</Tabs.List>
					</div>

					<div class="p-6 pt-4">
						<Tabs.Content value="manual" class="mt-0 space-y-4">
							<div class="space-y-2">
								<Label>Target values</Label>
								<FileUpload
									accept=".txt"
									bind:file={manualFile}
									bind:textValue={manualText}
									bind:mode={manualMode}
									onFileSelect={(file) => (manualFile = file)}
									onFileRemove={() => (manualFile = null)}
									onTextChange={(text) => (manualText = text)}
									placeholder="example.com
192.168.1.0/24
AS64512
https://app.example.com"
								/>
								<ImportHelpText type="text" />
							</div>
						</Tabs.Content>

						<Tabs.Content value="json" class="mt-0 space-y-4">
							<div class="space-y-2">
								<Label>JSON Data</Label>
								<FileUpload
									accept=".json"
									bind:file={jsonFile}
									bind:textValue={jsonText}
									bind:mode={jsonMode}
									onFileSelect={(file) => (jsonFile = file)}
									onFileRemove={() => (jsonFile = null)}
									onTextChange={(text) => (jsonText = text)}
									placeholder={`[\n  {\n    "target_value": "example.com",\n    "tags": ["production"],\n    "organizations": ["Acme Corp"]\n  }\n]`}
								/>
								<ImportHelpText type="json" />
							</div>
						</Tabs.Content>

						<Tabs.Content value="csv" class="mt-0 space-y-4">
							<div class="space-y-2">
								<Label>CSV File</Label>
								<FileUpload
									accept=".csv"
									bind:file={csvFile}
									onFileSelect={(file) => (csvFile = file)}
									onFileRemove={() => (csvFile = null)}
									onTextChange={() => {}}
									showTextInput={false}
								/>
								<ImportHelpText type="csv" />
							</div>
						</Tabs.Content>
					</div>
				</Tabs.Root>
			{:else if mode === 'preview'}
				<div class="p-6 space-y-4">
					<ImportPreview items={previewItems} maxHeight="400px" />
				</div>
			{:else if mode === 'results' && importResults}
				<div class="p-6">
					<ImportResults
						total={importResults.total}
						imported={importResults.imported}
						failed={importResults.failed}
						skipped_duplicates={importResults.skipped_duplicates}
						results={importResults.results}
					/>
				</div>
			{/if}
		</ScrollArea>

		<Separator />

		{#if mode !== 'results'}
			<QuickScanFields
				id="import-targets-scan"
				title="Scan after importing"
				description="Queues one scan per imported target."
				fallbackNote="Targets will be imported without a scan."
				storageKey={STORAGE_KEYS.importTargetsScanAfter}
				bind:enabled={scanAfterImport}
				bind:selection
				bind:contextId
				bind:armed={scanArmed}
				bind:pending={scanPending}
				disabled={busy}
			/>

			<Separator />
		{/if}

		{#if isProcessing && validateTotal > 0}
			<Progress value={validatePct} class="h-1 rounded-none" />
		{/if}
		<div class="flex items-center justify-between gap-2 p-4 bg-muted/30">
			{#if mode === 'input'}
				<Button variant="outline" disabled={busy} onclick={() => (open = false)}>Cancel</Button>
				<div class="flex gap-2">
					<Button
						variant="outline"
						onclick={handlePreview}
						disabled={!hasInput || isProcessing || isImporting}
					>
						{#if isProcessing}
							<Spinner />
							Processing…
						{:else}
							<Eye class="h-4 w-4 mr-2" />
							Preview
						{/if}
					</Button>
					<Button
						onclick={handleDirectImport}
						disabled={!hasInput || isProcessing || isImporting || scanPending}
					>
						{#if isImporting}
							<Spinner />
							{scanArmed ? 'Queuing…' : 'Importing…'}
						{:else if scanArmed}
							<Rocket class="h-4 w-4 mr-2" />
							Import & scan
						{:else}
							<Upload class="h-4 w-4 mr-2" />
							Import
						{/if}
					</Button>
				</div>
			{:else if mode === 'preview'}
				<Button variant="outline" onclick={() => (mode = 'input')}>Back</Button>
				<Button
					onclick={handleImportFromPreview}
					disabled={!canImport || isImporting || scanPending}
				>
					{#if isImporting}
						<Spinner />
						{scanArmed ? 'Queuing…' : 'Importing…'}
					{:else if scanArmed}
						<Rocket class="h-4 w-4 mr-2" />
						Import & scan {previewItems.filter((item) => !item.error).length}
					{:else}
						Import {previewItems.filter((item) => !item.error).length}
					{/if}
				</Button>
			{:else}
				<Button variant="outline" onclick={handleImportMore} disabled={isImporting}>
					Import more
				</Button>
				<div class="flex items-center gap-2">
					{#if isImporting}
						<span class="flex items-center gap-2 text-xs text-muted-foreground">
							<Spinner class="h-3.5 w-3.5" />
							Queuing scans…
						</span>
					{:else if queuedScans > 0}
						<span class="text-xs text-muted-foreground">
							{queuedScans} scan{queuedScans !== 1 ? 's' : ''} queued
						</span>
					{/if}
					<Button variant="outline" onclick={() => (open = false)} disabled={isImporting}>
						<CircleCheck class="h-4 w-4 mr-2" />
						Done
					</Button>
					{#if queuedScans > 0}
						<Button onclick={viewScans} disabled={isImporting}>
							<Rocket class="h-4 w-4 mr-2" />
							View scans
						</Button>
					{:else if importedIds.length > 0}
						<Button onclick={scanImported} disabled={isImporting}>
							<Rocket class="h-4 w-4 mr-2" />
							Scan {importedIds.length} target{importedIds.length !== 1 ? 's' : ''}
						</Button>
					{/if}
				</div>
			{/if}
		</div>
	</Dialog.Content>
</Dialog.Root>

<LaunchDialog
	bind:open={showLaunch}
	targetIds={launchIds}
	onClose={() => {
		showLaunch = false;
		launchIds = undefined;
	}}
/>
