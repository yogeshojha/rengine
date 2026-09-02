<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Badge } from '$lib/components/ui/badge';
	import * as Alert from '$lib/components/ui/alert';
	import LoadingButton from '@/components/loading-button.svelte';
	import AlertTriangle from '@lucide/svelte/icons/alert-triangle';
	import Upload from '@lucide/svelte/icons/upload';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import { parse, validate, draftFromDoc } from '$lib/utilities/engine-yaml';
	import { summarize, FOOTPRINT_LABEL } from '$lib/utilities/engine-summary';
	import type { EngineCatalog } from '$lib/types/scan-engine';

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

	async function handleDrop(event: DragEvent) {
		event.preventDefault();
		dragging = false;
		const file = event.dataTransfer?.files?.[0];
		if (file) source = await file.text();
	}
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content class="sm:max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>Import engine</Dialog.Title>
			<Dialog.Description>
				Paste or drop an engine YAML. You'll see what it does before it's created.
			</Dialog.Description>
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
			<Textarea
				bind:value={source}
				placeholder={PLACEHOLDER}
				class="min-h-[220px] resize-none border-0 bg-transparent font-mono text-xs shadow-none focus-visible:ring-0"
				spellcheck={false}
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
					{errors.length} problem{errors.length === 1 ? '' : 's'} — nothing will be imported
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
			<div class="preview">
				<div class="preview-head">
					<span class="preview-name">{parsed.name || 'Untitled engine'}</span>
					<Badge variant="outline" class="cap">{parsed.intensity}</Badge>
					<Badge variant="outline" class="cap">
						{#if summary.footprint === 'none'}<EyeOff size={10} />{/if}
						{FOOTPRINT_LABEL[summary.footprint]}
					</Badge>
				</div>
				<p class="preview-line">{summary.headline}</p>
				{#if summary.tools.length}
					<p class="preview-tools">{summary.tools.join(' · ')}</p>
				{/if}
			</div>
		{/if}

		<Dialog.Footer>
			<Button variant="outline" onclick={() => onOpenChange(false)}>Cancel</Button>
			<LoadingButton loading={isImporting} disabled={!canImport} onclick={() => onImport(source)}>
				Import engine
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<style>
	.drop {
		position: relative;
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
		bottom: 8px;
		display: inline-flex;
		align-items: center;
		gap: 5px;
		font-size: 11px;
		color: var(--muted-foreground);
		pointer-events: none;
	}

	.preview {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 11px 13px;
		border: 1px solid var(--border);
		border-radius: 0.6rem;
		background: var(--muted);
	}
	.preview-head {
		display: flex;
		align-items: center;
		gap: 7px;
		flex-wrap: wrap;
	}
	.preview-name {
		font-size: 13px;
		font-weight: 600;
	}
	.preview-head :global(.cap) {
		gap: 3px;
		font-size: 10px;
		font-weight: 400;
		text-transform: capitalize;
	}
	.preview-line {
		font-size: 12px;
		color: var(--muted-foreground);
	}
	.preview-tools {
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 10.5px;
		color: var(--muted-foreground);
		opacity: 0.8;
	}
</style>
