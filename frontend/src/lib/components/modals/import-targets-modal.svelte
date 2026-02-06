<script lang="ts">
	import { FileText, Code, List, CircleCheck, Eye, Upload, ExternalLink } from 'lucide-svelte';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Tabs from '$lib/components/ui/tabs';
	import { Separator } from '$lib/components/ui/separator';
	import FileUpload from '$lib/components/targets/file-upload.svelte';
	import ImportPreview from '$lib/components/targets/import-preview.svelte';
	import ImportResults from '$lib/components/targets/import-results.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { toast } from 'svelte-sonner';
	import ImportHelpText from '$lib/components/targets/import-helper.svelte';

	interface Props {
		open: boolean;
	}

	let { open = $bindable() }: Props = $props();

	type ImportMode = 'input' | 'preview' | 'results';
	type ImportMethod = 'manual' | 'json' | 'csv';

	let mode = $state<ImportMode>('input');
	let activeTab = $state<ImportMethod>('manual');

	// Input states
	let manualText = $state('');
	let manualFile = $state<File | null>(null);
	let manualMode = $state<'text' | 'file'>('text');

	let jsonText = $state('');
	let jsonFile = $state<File | null>(null);
	let jsonMode = $state<'text' | 'file'>('text');

	let csvFile = $state<File | null>(null);

	// Preview state
	let previewItems = $state<any[]>([]);

	// Results state
	let importResults = $state<any>(null);

	// Loading states
	let isProcessing = $state(false);
	let isImporting = $state(false);

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
	}

	function handleOpenChange(isOpen: boolean) {
		if (!isOpen) {
			resetModal();
		}
		open = isOpen;
	}

	// Parse manual input
	function parseManualInput(text: string) {
		return text
			.split('\n')
			.map((line) => line.trim())
			.filter((line) => line.length > 0)
			.map((target_value) => ({ target_value }));
	}

	// Parse JSON input
	function parseJsonInput(text: string) {
		try {
			const parsed = JSON.parse(text);

			// Handle array format
			if (Array.isArray(parsed)) {
				return parsed.map((item) => {
					if (typeof item === 'string') {
						return { target_value: item };
					}
					return item;
				});
			}

			// Handle object with targets array
			if (parsed.targets && Array.isArray(parsed.targets)) {
				return parsed.targets;
			}

			throw new Error('Invalid JSON format');
		} catch (e) {
			throw new Error(
				'Invalid JSON format. Expected array of targets or object with "targets" array.'
			);
		}
	}

	// Parse CSV file
	async function parseCsvFile(file: File): Promise<any[]> {
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

					// Check if first line is header
					const firstLine = lines[0].toLowerCase();
					const hasHeaders =
						firstLine.includes('target') ||
						firstLine.includes('domain') ||
						firstLine.includes('value') ||
						firstLine.includes('ip');

					const dataLines = hasHeaders ? lines.slice(1) : lines;

					// Parse CSV
					const items = dataLines.map((line) => {
						const parts = line.split(',').map((p) => p.trim().replace(/^["']|["']$/g, ''));

						const item: any = {
							target_value: parts[0]
						};

						// Handle additional columns
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
				} catch (e) {
					reject(new Error('Failed to parse CSV file'));
				}
			};

			reader.onerror = () => reject(new Error('Failed to read file'));
			reader.readAsText(file);
		});
	}

	// Read text file
	async function readTextFile(file: File): Promise<string> {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = (e) => resolve(e.target?.result as string);
			reader.onerror = () => reject(new Error('Failed to read file'));
			reader.readAsText(file);
		});
	}

	// Process input and get items
	async function getInputItems(): Promise<any[]> {
		let items: any[] = [];

		if (activeTab === 'manual') {
			const source = manualMode === 'text' ? manualText : manualFile;
			if (!source) {
				toast.error('Please enter targets or upload a file');
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
				toast.error('Please enter JSON data or upload a file');
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
				toast.error('Please select a CSV file');
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

	// Handle preview
	async function handlePreview() {
		isProcessing = true;

		try {
			const items = await getInputItems();
			if (items.length === 0) {
				isProcessing = false;
				return;
			}

			// Validate each target
			const validated = await Promise.all(
				items.map(async (item) => {
					try {
						const result = await targetsApi.validate({
							target_value: item.target_value
						});

						return {
							...item,
							target_type: result.valid ? result.target_type : null,
							error: result.valid ? undefined : result.error || 'Invalid target'
						};
					} catch {
						return {
							...item,
							error: 'Validation failed'
						};
					}
				})
			);

			previewItems = validated;
			mode = 'preview';
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to process input');
		} finally {
			isProcessing = false;
		}
	}

	// Handle direct import (skip preview)
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

	// Handle import from preview
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

	// Execute import
	async function executeImport(items: any[]) {
		const projectSlug = projectsStore.activeProject?.slug;
		if (!projectSlug) return;

		try {
			let response;

			if (activeTab === 'csv' && csvFile) {
				// Use CSV file upload endpoint
				response = await targetsApi.importCsv(projectSlug, csvFile);
			} else {
				// Use JSON import endpoint for manual and JSON
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

			// Refresh targets store
			await targetsStore.refresh();

			if (response.imported > 0) {
				toast.success(
					`Successfully imported ${response.imported} target${response.imported !== 1 ? 's' : ''}`
				);
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
	<Dialog.Content class="sm:max-w-[700px] gap-0 p-0 max-h-[85vh] flex flex-col">
		<Dialog.Header class="p-6 pb-4">
			<Dialog.Title>Import Targets</Dialog.Title>
			<Dialog.Description>
				{#if mode === 'input'}
					Import multiple targets from various sources
				{:else if mode === 'preview'}
					Review targets before importing
				{:else}
					Import complete
				{/if}
			</Dialog.Description>
		</Dialog.Header>

		<Separator />

		<div class="flex-1 overflow-y-auto">
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
						<!-- Manual Input -->
						<Tabs.Content value="manual" class="mt-0 space-y-4">
							<div class="space-y-2">
								<Label>Target Values</Label>
								<FileUpload
									accept=".txt"
									bind:file={manualFile}
									bind:textValue={manualText}
									bind:mode={manualMode}
									onFileSelect={(file) => (manualFile = file)}
									onFileRemove={() => (manualFile = null)}
									onTextChange={(text) => (manualText = text)}
									placeholder={`example.com\n192.168.1.0/24\nAS64512\nhttps://app.example.com`}
								/>
								<ImportHelpText type="text" />
							</div>
						</Tabs.Content>

						<!-- JSON Input -->
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

						<!-- CSV Upload -->
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
		</div>

		<Separator />

		<div class="flex items-center justify-between gap-2 p-4 bg-muted/30">
			{#if mode === 'input'}
				<Button variant="outline" onclick={() => (open = false)}>Cancel</Button>
				<div class="flex gap-2">
					<Button
						variant="outline"
						onclick={handlePreview}
						disabled={!hasInput || isProcessing || isImporting}
					>
						{#if isProcessing}
							<Spinner />
							Processing...
						{:else}
							<Eye class="h-4 w-4 mr-2" />
							Preview
						{/if}
					</Button>
					<Button onclick={handleDirectImport} disabled={!hasInput || isProcessing || isImporting}>
						{#if isImporting}
							<Spinner />
							Importing...
						{:else}
							<Upload class="h-4 w-4 mr-2" />
							Import
						{/if}
					</Button>
				</div>
			{:else if mode === 'preview'}
				<Button variant="outline" onclick={() => (mode = 'input')}>Back</Button>
				<Button onclick={handleImportFromPreview} disabled={!canImport || isImporting}>
					{#if isImporting}
						<Spinner />
						Importing...
					{:else}
						Import {previewItems.filter((item) => !item.error).length}
					{/if}
				</Button>
			{:else}
				<div></div>
				<div class="flex gap-2">
					<Button variant="outline" onclick={handleImportMore}>Import More</Button>
					<Button onclick={() => (open = false)}>
						<CircleCheck class="h-4 w-4 mr-2" />
						Done
					</Button>
				</div>
			{/if}
		</div>
	</Dialog.Content>
</Dialog.Root>
