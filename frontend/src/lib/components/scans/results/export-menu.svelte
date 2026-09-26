<script lang="ts">
	import { errorMessage } from '$lib/utilities/errors';
	import Download from '@lucide/svelte/icons/download';
	import History from '@lucide/svelte/icons/history';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { EXPORT_FORMATS, FORMAT_LABELS, isLive } from '$lib/config/exports';
	import { exportsStore } from '$lib/stores/exports.svelte';
	import { SurfaceDimension } from '$lib/config/surface';
	import type { ExportRead } from '$lib/types/export';
	import ExportsSheet from './exports-sheet.svelte';

	interface Props {
		dimension: string;
		projectId: string;
		scanId?: string;
		targetId?: string;
		filters: Record<string, unknown>;
		disabled?: boolean;
		ids?: string[];
		compact?: boolean;
	}

	let {
		dimension,
		projectId,
		scanId = '',
		targetId = '',
		filters,
		disabled = false,
		ids = [],
		compact = false
	}: Props = $props();

	let sheetOpen = $state(false);
	let pending = $state(false);
	let withEvidence = $state(false);

	// only findings carry a stored request and response
	let offersEvidence = $derived(dimension === SurfaceDimension.VULNERABILITIES);

	let live = $derived(exportsStore.rows.some((row) => isLive(row.status)));

	function ready(row: ExportRead) {
		pending = false;
		if (row.status !== 'completed') {
			toast.error(row.error || 'Export not written.');
			return;
		}
		const capped = row.capped ? ` of ${row.total_rows.toLocaleString()}` : '';
		toast.success(`${row.row_count.toLocaleString()}${capped} rows exported`);
		window.location.href = exportsStore.downloadUrl(row.id);
	}

	async function start(format: string) {
		if (!projectId) return;
		pending = true;
		try {
			await exportsStore.create(
				projectId,
				{
					dimension,
					scan_id: scanId || null,
					target_id: targetId || null,
					export_format: format,
					include_evidence: offersEvidence && withEvidence,
					filters: {
						...filters,
						ids: ids.length ? ids : undefined,
						limit: undefined,
						offset: undefined,
						page: undefined,
						size: undefined
					}
				},
				ready
			);
		} catch (e) {
			pending = false;
			toast.error(errorMessage(e, 'Export not started.'));
		}
	}

	function openHistory() {
		sheetOpen = true;
	}
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger>
		{#snippet child({ props })}
			<Button
				{...props}
				variant={compact ? 'ghost' : 'outline'}
				size="sm"
				class={compact ? 'gap-2 font-medium' : 'h-9 gap-2'}
				disabled={disabled || !projectId}
			>
				{#if pending || live}
					<Spinner class={compact ? 'size-3.5' : 'size-4'} />
				{:else}
					<Download class={compact ? 'size-3.5 text-muted-foreground' : 'size-4'} />
				{/if}
				<span class={compact ? '' : 'hidden sm:inline'}>Export</span>
			</Button>
		{/snippet}
	</DropdownMenu.Trigger>
	<DropdownMenu.Content align={compact ? 'center' : 'end'} class="w-48">
		<DropdownMenu.Label>{compact ? 'Export selection' : 'Export this view'}</DropdownMenu.Label>
		<DropdownMenu.Separator />
		{#each EXPORT_FORMATS as format (format)}
			<DropdownMenu.Item onclick={() => start(format)}>
				{FORMAT_LABELS[format]}
			</DropdownMenu.Item>
		{/each}
		{#if offersEvidence}
			<DropdownMenu.Separator />
			<DropdownMenu.CheckboxItem
				checked={withEvidence}
				onCheckedChange={(value) => (withEvidence = value)}
				closeOnSelect={false}
			>
				Include request and response
			</DropdownMenu.CheckboxItem>
			<p class="px-2 pb-1 text-2xs text-muted-foreground">
				Adds the stored request and response. Scan headers are masked. Response bodies are not.
			</p>
		{/if}
		{#if !compact}
			<DropdownMenu.Separator />
			<DropdownMenu.Item onclick={openHistory}>
				<History class="size-3.5" />
				Past exports
			</DropdownMenu.Item>
		{/if}
	</DropdownMenu.Content>
</DropdownMenu.Root>

{#if !compact}
	<ExportsSheet bind:open={sheetOpen} {projectId} {scanId} {targetId} />
{/if}
