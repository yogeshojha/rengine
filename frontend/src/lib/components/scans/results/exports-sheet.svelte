<script lang="ts">
	import Download from '@lucide/svelte/icons/download';
	import RotateCw from '@lucide/svelte/icons/rotate-cw';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Progress } from '$lib/components/ui/progress';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Spinner } from '$lib/components/ui/spinner';
	import * as Sheet from '$lib/components/ui/sheet';
	import EmptyState from '$lib/components/empty-state.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import Hint from '$lib/components/hint.svelte';
	import RowSkeleton from '$lib/components/skeleton/row-skeleton.svelte';
	import {
		BUNDLE,
		BUNDLE_LABEL,
		EXPORT_STATUS_LABELS,
		EXPORT_STATUS_TONE,
		ExportStatus,
		FORMAT_LABELS,
		isLive
	} from '$lib/config/exports';
	import { formatBytes } from '$lib/utilities/format';
	import { surfaceSpec } from '$lib/config/surface';
	import { exportsStore } from '$lib/stores/exports.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import type { ExportRead } from '$lib/types/export';
	import FileDown from '@lucide/svelte/icons/file-down';

	interface Props {
		open: boolean;
		projectId: string;
		scanId?: string;
		targetId?: string;
	}

	let { open = $bindable(false), projectId, scanId = '', targetId = '' }: Props = $props();

	let loadedFor = $state('');
	let failed = $state(false);
	let removing = $state<ExportRead | null>(null);
	let busy = $state(false);

	async function load() {
		failed = false;
		try {
			await exportsStore.load(projectId, { scanId, targetId });
		} catch {
			failed = true;
		}
	}

	$effect(() => {
		if (!open || !projectId) return;
		const key = `${projectId}:${scanId}:${targetId}`;
		if (loadedFor === key) return;
		loadedFor = key;
		void load();
	});

	function label(dimension: string): string {
		if (dimension === BUNDLE) return BUNDLE_LABEL;
		return surfaceSpec(dimension)?.label ?? dimension;
	}

	async function rerun(id: string) {
		try {
			await exportsStore.rerun(id);
			toast.success('Export started');
		} catch {
			toast.error('Export not started');
		}
	}

	async function remove() {
		if (!removing) return;
		busy = true;
		try {
			await exportsStore.remove(removing.id);
			removing = null;
		} catch {
			toast.error('Export not deleted');
		} finally {
			busy = false;
		}
	}
</script>

<Sheet.Root bind:open>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-lg">
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title>Past exports</Sheet.Title>
			<Sheet.Description>
				{scanId
					? 'Exports from this run.'
					: targetId
						? 'Exports from this target.'
						: 'Exports across this project.'}
			</Sheet.Description>
		</Sheet.Header>

		<ScrollArea class="min-h-0 flex-1">
			<div class="flex flex-col">
				{#if exportsStore.loading && exportsStore.rows.length === 0}
					<RowSkeleton rows={3} avatar={null} trailing="h-7 w-20 rounded-md" padding="px-5" />
				{:else if failed}
					<EmptyState
						icon={TriangleAlert}
						title="Exports not loaded"
						compact
						class="rounded-none border-0 bg-transparent py-16"
					>
						<Button variant="outline" size="sm" onclick={() => void load()}>Retry</Button>
					</EmptyState>
				{:else if exportsStore.rows.length === 0}
					<EmptyState
						icon={FileDown}
						title="No exports"
						compact
						class="rounded-none border-0 bg-transparent py-16"
					/>
				{:else}
					{#each exportsStore.rows as row (row.id)}
						{@const live = isLive(row.status)}
						<div class="flex flex-col gap-1.5 border-b px-5 py-3 last:border-b-0">
							<div class="flex items-start justify-between gap-3">
								<div class="flex min-w-0 flex-col gap-0.5">
									<span class="truncate text-sm font-medium">{label(row.dimension)}</span>
									{#if row.subject !== label(row.dimension)}
										<span class="truncate text-xs text-muted-foreground">{row.subject}</span>
									{/if}
								</div>
								<div class="flex shrink-0 items-center gap-1">
									{#if row.status === ExportStatus.COMPLETED}
										<Button
											variant="outline"
											size="sm"
											class="h-7"
											href={exportsStore.downloadUrl(row.id)}
											download
										>
											<Download class="size-3.5" />
											{FORMAT_LABELS[row.export_format] ?? row.export_format}
										</Button>
									{/if}
									<Hint text="Run again">
										{#snippet child(props)}
											<Button
												{...props}
												variant="ghost"
												size="icon"
												class="size-7"
												disabled={live}
												onclick={() => rerun(row.id)}
												aria-label="Run again"
											>
												<RotateCw class="size-3.5" />
											</Button>
										{/snippet}
									</Hint>
									<Button
										variant="ghost"
										size="icon"
										class="size-7"
										disabled={live}
										onclick={() => (removing = row)}
										aria-label="Delete export"
									>
										<Trash2 class="size-3.5" />
									</Button>
								</div>
							</div>

							<div
								class="flex flex-wrap items-center gap-x-2 gap-y-1 text-2xs text-muted-foreground"
							>
								<span class={EXPORT_STATUS_TONE[row.status]}>
									{EXPORT_STATUS_LABELS[row.status] ?? row.status}
								</span>
								{#if row.status === ExportStatus.COMPLETED}
									<span>·</span>
									<span class="tabular-nums">
										{row.row_count.toLocaleString()}{row.capped
											? ` of ${row.total_rows.toLocaleString()}`
											: ''} rows
									</span>
									{#if row.bytes_written}
										<span>·</span>
										<span>{formatBytes(row.bytes_written)}</span>
									{/if}
								{/if}
								<span>·</span>
								<span>{relativeTime(row.created_at)}</span>
							</div>

							{#if row.query}
								<code class="truncate rounded bg-muted px-1.5 py-0.5 font-mono text-2xs">
									{row.query}
								</code>
							{/if}

							{#if live}
								<div class="flex items-center gap-2 pt-0.5">
									<Spinner class="size-3" />
									<span class="text-xs text-muted-foreground">{row.step || 'Working'}</span>
									<Progress value={row.progress} class="h-1 max-w-40" />
								</div>
							{/if}

							{#if row.error}
								<p class="flex items-start gap-1.5 text-2xs text-destructive">
									<TriangleAlert class="mt-px size-3 shrink-0" />
									<span>{row.error}</span>
								</p>
							{/if}
						</div>
					{/each}
				{/if}
			</div>
		</ScrollArea>
	</Sheet.Content>
</Sheet.Root>

<ConfirmDialog
	open={removing !== null}
	title="Delete export"
	description={removing
		? `${label(removing.dimension)} ${FORMAT_LABELS[removing.export_format] ?? removing.export_format} export ${removing.status === ExportStatus.COMPLETED ? 'and its file are' : 'is'} removed.`
		: ''}
	confirmLabel="Delete"
	loadingLabel="Deleting"
	destructive
	loading={busy}
	onOpenChange={(value) => {
		if (!value) removing = null;
	}}
	onConfirm={remove}
/>
