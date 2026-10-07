<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import * as Alert from '$lib/components/ui/alert';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import Upload from '@lucide/svelte/icons/upload';
	import YamlEditor from '$lib/components/yaml-editor.svelte';
	import StageList from './stage-list.svelte';
	import FootprintMeter from './footprint-meter.svelte';
	import { parse, validate, draftFromDoc } from '$lib/utilities/engine-yaml';
	import { summarize } from '$lib/utilities/engine-summary';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import { INTENSITY_LABELS, type EngineCatalog } from '$lib/types/scan-engine';

	interface Props {
		open: boolean;
		catalog: EngineCatalog | null;
		isImporting: boolean;
		onOpenChange: (open: boolean) => void;
		onImport: (yaml: string) => void;
	}

	let { open, catalog, isImporting, onOpenChange, onImport }: Props = $props();

	const PLACEHOLDER = `name: Shared Recon
intensity: normal
stages:
  subdomain_discovery:
    enabled: true`;

	let source = $state('');
	let dragging = $state(false);

	$effect(() => {
		if (open) source = '';
	});

	const doc = $derived(source.trim() ? parse(source) : null);
	const issues = $derived(doc ? validate(source, doc, catalog) : []);
	const errors = $derived(issues.filter((i) => i.severity === 'error'));
	const parsed = $derived(doc && !doc.errors.length ? draftFromDoc(doc) : null);
	const summary = $derived(parsed ? summarize(parsed.stages, catalog, parsed.intensity) : null);
	const canImport = $derived(Boolean(parsed) && errors.length === 0 && !isImporting);
	const guard = new DiscardGuard(
		() => source.trim() !== '',
		() => onOpenChange(false)
	);

	async function handleDrop(event: DragEvent) {
		event.preventDefault();
		dragging = false;
		const file = event.dataTransfer?.files?.[0];
		if (file) source = await file.text();
	}

	function requestOpen(next: boolean) {
		if (next) onOpenChange(true);
		else if (!isImporting) guard.close();
	}
</script>

<Dialog.Root bind:open={() => open, requestOpen}>
	<Dialog.Content class="sm:max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>Import engine</Dialog.Title>
			<Dialog.Description>Paste or drop an engine YAML document.</Dialog.Description>
		</Dialog.Header>

		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="drop"
			class:dragging
			ondragover={(e) => {
				e.preventDefault();
				dragging = true;
			}}
			ondragleave={() => (dragging = false)}
			ondrop={handleDrop}
		>
			<YamlEditor
				value={source}
				{issues}
				filename="engine.yaml"
				placeholder={PLACEHOLDER}
				onChange={(next) => (source = next)}
			/>
			{#if !source.trim()}
				<div class="hint">
					<Upload size={13} />
					drop a .yaml file
				</div>
			{/if}
		</div>

		{#if source.trim() && errors.length}
			<Alert.Root variant="destructive">
				<AlertTriangle />
				<Alert.Title>
					{errors.length} problem{errors.length === 1 ? '' : 's'}
				</Alert.Title>
				<Alert.Description>
					<ul class="list-inside list-disc space-y-0.5 text-xs">
						{#each errors.slice(0, 5) as issue (issue.message + issue.line)}
							<li>line {issue.line}: {issue.message}</li>
						{/each}
					</ul>
				</Alert.Description>
			</Alert.Root>
		{:else if parsed && summary}
			<ScrollArea class="min-h-0 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(92vh-32rem)]">
				<div class="preview">
					<div class="preview-head">
						<span class="preview-name">{parsed.name || 'Untitled engine'}</span>
						<Badge variant="outline" class="cap"
							>{INTENSITY_LABELS[parsed.intensity] ?? parsed.intensity}</Badge
						>
					</div>
					{#if catalog}
						<StageList
							stages={catalog.stages}
							config={parsed.stages}
							intensity={parsed.intensity}
							class="py-1"
						/>
					{/if}
					<div class="preview-line">
						<span>{summary.activeStages} of {summary.totalStages} stages run</span>
						<FootprintMeter
							footprint={summary.footprint}
							requestsPerSecond={summary.requestsPerSecond}
						/>
					</div>
					{#if summary.tools.length}
						<p class="preview-tools">{summary.tools.join(' · ')}</p>
					{/if}
				</div>
			</ScrollArea>
		{/if}

		<Dialog.Footer>
			<Button variant="outline" disabled={isImporting} onclick={() => guard.close()}>Cancel</Button>
			<LoadingButton
				loading={isImporting}
				loadingLabel="Importing"
				disabled={!canImport}
				onclick={() => onImport(source)}
			>
				Import engine
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>

<style>
	.drop {
		position: relative;
		height: 17rem;
		overflow: hidden;
		border: 1px dashed var(--border);
		border-radius: 0.6rem;
		transition:
			border-color 0.15s ease,
			background 0.15s ease;
	}
	.drop.dragging {
		border-color: var(--primary);
		background: color-mix(in oklch, var(--primary) 6%, transparent);
	}
	.hint {
		position: absolute;
		right: 10px;
		bottom: 36px;
		display: inline-flex;
		align-items: center;
		gap: calc(var(--spacing) * 1);
		font-size: var(--text-2xs);
		color: var(--muted-foreground);
		pointer-events: none;
	}

	.preview {
		display: flex;
		flex-direction: column;
		gap: calc(var(--spacing) * 1);
		padding: calc(var(--spacing) * 2.5) calc(var(--spacing) * 3);
		border: 1px solid var(--border);
		border-radius: 0.6rem;
		background: var(--muted);
	}
	.preview-head {
		display: flex;
		align-items: center;
		gap: calc(var(--spacing) * 1.5);
		flex-wrap: wrap;
	}
	.preview-name {
		font-size: var(--text-sm);
		font-weight: 600;
	}
	.preview-head :global(.cap) {
		gap: calc(var(--spacing) * 0.5);
		font-size: var(--text-2xs);
		font-weight: 400;
	}
	.preview-line {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: calc(var(--spacing) * 2);
		flex-wrap: wrap;
		font-size: var(--text-xs);
		color: var(--muted-foreground);
	}
	.preview-tools {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: var(--text-2xs);
		color: var(--muted-foreground);
		opacity: 0.8;
	}
</style>
