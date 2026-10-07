<script lang="ts">
	import Download from '@lucide/svelte/icons/download';
	import History from '@lucide/svelte/icons/history';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { EXPORT_FORMATS, ExportStatus, FORMAT_LABELS, isLive } from '$lib/config/exports';
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
		ids?: string[];
		compact?: boolean;
	}

	let {
		dimension,
		projectId,
		scanId = '',
		targetId = '',
		filters,
		ids = [],
		compact = false
	}: Props = $props();

	let sheetOpen = $state(false);
	let pending = $state(false);
	let withEvidence = $state(false);

	let offersEvidence = $derived(dimension === SurfaceDimension.VULNERABILITIES);

	let live = $derived(exportsStore.rows.some((row) => isLive(row.status)));

	function ready(row: ExportRead) {
		pending = false;
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
			toast.error(e instanceof Error ? e.message : 'Export not started');
		}
	}

	function openHistory() {
		sheetOpen = true;
	}
</script>

<DropdownMenu.Root>
	<Tooltip.Root>
		<Tooltip.Trigger>
			{#snippet child({ props: tip })}
				<DropdownMenu.Trigger {...tip}>
					{#snippet child({ props })}
						<Button
							{...props}
							variant={compact ? 'ghost' : 'outline'}
							size={compact ? 'sm' : 'default'}
							disabled={!projectId}
							aria-label="Export"
						>
							{#if pending || live}
								<Spinner class={compact ? 'size-3.5' : 'size-4'} />
							{:else}
								<Download class={compact ? 'size-3.5 text-muted-foreground' : 'size-4'} />
							{/if}
							<span class={compact ? '' : 'hidden 2xl:inline'}>Export</span>
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
			{/snippet}
		</Tooltip.Trigger>
		<Tooltip.Content class={compact ? 'hidden' : '2xl:hidden'}>Export</Tooltip.Content>
	</Tooltip.Root>
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
