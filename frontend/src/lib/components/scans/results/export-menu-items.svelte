<script lang="ts">
	import History from '@lucide/svelte/icons/history';
	import { toast } from 'svelte-sonner';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { EXPORT_FORMATS, ExportStatus, FORMAT_LABELS } from '$lib/config/exports';
	import { exportsStore } from '$lib/stores/exports.svelte';
	import { SurfaceDimension } from '$lib/config/surface';
	import type { ExportRead } from '$lib/types/export';

	interface Props {
		dimension: string;
		projectId: string;
		scanId?: string;
		targetId?: string;
		filters: Record<string, unknown>;
		ids?: string[];
		/** opens the past exports sheet */
		onHistory?: () => void;
		onPending?: (pending: boolean) => void;
		withEvidence?: boolean;
	}

	let {
		dimension,
		projectId,
		scanId = '',
		targetId = '',
		filters,
		ids = [],
		onHistory,
		onPending,
		withEvidence = $bindable(false)
	}: Props = $props();

	let offersEvidence = $derived(dimension === SurfaceDimension.VULNERABILITIES);

	function ready(row: ExportRead) {
		onPending?.(false);
		if (row.status !== ExportStatus.COMPLETED) {
			toast.error(row.error || 'Export not written');
			return;
		}
		const capped = row.capped ? ` of ${row.total_rows.toLocaleString()}` : '';
		toast.success(`${row.row_count.toLocaleString()}${capped} rows exported`);
		window.location.href = exportsStore.downloadUrl(row.id);
	}

	async function start(format: string) {
		if (!projectId) return;
		onPending?.(true);
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
			onPending?.(false);
			toast.error(e instanceof Error ? e.message : 'Export not started');
		}
	}
</script>

{#each EXPORT_FORMATS as format (format)}
	<DropdownMenu.Item onclick={() => start(format)} disabled={!projectId}>
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
		Scan headers are masked. Response bodies are not.
	</p>
{/if}
{#if onHistory}
	<DropdownMenu.Separator />
	<DropdownMenu.Item onclick={() => onHistory()}>
		<History class="size-3.5" />
		Past exports
	</DropdownMenu.Item>
{/if}
