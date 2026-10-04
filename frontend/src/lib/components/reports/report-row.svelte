<script lang="ts">
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Progress } from '$lib/components/ui/progress/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import EllipsisIcon from '@lucide/svelte/icons/ellipsis';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import {
		FORMAT_ICONS,
		FORMAT_LABELS,
		REPORT_STATUS_LABELS,
		REPORT_STATUS_TONE,
		ReportFormat,
		ReportStatus,
		isLive
	} from '$lib/config/reports';
	import { formatBytes, formatSeconds } from '$lib/utilities/format';
	import { reportsApi } from '$lib/api/reports';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import Hint from '$lib/components/hint.svelte';
	import ThemePreview from './theme-preview.svelte';
	import ReportPreviewDialog from './preview/report-preview-dialog.svelte';
	import type { Report } from '$lib/types/report';

	let {
		report,
		projectId,
		isSelected = false,
		onSelect,
		onRetry,
		onDelete
	}: {
		report: Report;
		projectId: string;
		isSelected?: boolean;
		onSelect: (id: string) => void;
		onRetry: (id: string) => void;
		onDelete: (id: string) => void;
	} = $props();

	const live = $derived(isLive(report.status));
	const failed = $derived(report.status === ReportStatus.FAILED);
	const primary = $derived(report.files[0]);
	const theme = $derived(reportCatalog.theme(report.theme));
	const previewable = $derived(report.files.some((f) => f.format === ReportFormat.PDF));
	const warnings = $derived(
		report.status === ReportStatus.COMPLETED && Array.isArray(report.stats.warnings)
			? (report.stats.warnings as string[])
			: []
	);

	let previewOpen = $state(false);
</script>

<div
	class="group flex items-start gap-3 border-b px-4 py-3.5 transition-colors last:border-b-0 {isSelected
		? 'bg-primary/5'
		: ''}"
>
	<div class="flex h-5 shrink-0 items-center sm:h-auto sm:self-center">
		<Checkbox
			checked={isSelected}
			onCheckedChange={() => onSelect(report.id)}
			aria-label="Select {report.title}"
			class="transition-opacity {isSelected
				? 'opacity-100'
				: 'opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100'}"
		/>
	</div>
	<div class="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center">
		{#if theme}
			<div class="hidden w-9 shrink-0 self-start sm:block">
				{#if previewable}
					<button
						type="button"
						onclick={() => (previewOpen = true)}
						class="focus-visible:ring-ring block w-full rounded-[3px] focus-visible:ring-2 focus-visible:outline-none"
						aria-label="Preview {report.title}"
					>
						<ThemePreview {theme} variant="cover" class="shadow-sm" />
					</button>
				{:else}
					<ThemePreview {theme} variant="cover" class="shadow-sm" />
				{/if}
			</div>
		{/if}
		<div class="min-w-0 flex-1 space-y-1">
			<div class="flex flex-wrap items-center gap-2">
				{#if previewable}
					<button
						type="button"
						onclick={() => (previewOpen = true)}
						class="min-w-0 text-left font-medium break-words hover:text-primary"
					>
						{report.title}
					</button>
				{:else}
					<span class="min-w-0 font-medium break-words">{report.title}</span>
				{/if}
				<Badge variant="outline" class="max-w-full font-mono text-2xs break-all whitespace-normal"
					>{report.subject}</Badge
				>
				{#if report.ai_used}
					<Badge variant="info">AI</Badge>
				{/if}
			</div>
			<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
				<span class={REPORT_STATUS_TONE[report.status]}>
					{REPORT_STATUS_LABELS[report.status] ?? report.status}
				</span>
				<span>{report.template_name}</span>
				{#if report.page_count}<span>{report.page_count} pages</span>{/if}
				{#if report.duration_seconds}<span>{formatSeconds(report.duration_seconds)}</span>{/if}
				<span>{relativeTime(report.created_at)}</span>
				{#if warnings.length}
					<Hint text={warnings.join(' · ')}>
						{#snippet child(props)}
							<span {...props} class="flex items-center gap-1 text-warning">
								<TriangleAlertIcon class="size-3" />
								{plural(warnings.length, 'warning')}
							</span>
						{/snippet}
					</Hint>
				{/if}
			</div>
			{#if live}
				<div class="flex items-center gap-2 pt-1">
					<Spinner class="size-3" />
					<span class="text-xs text-muted-foreground">{report.step || 'Working'}</span>
					<Progress value={report.progress} class="h-1 max-w-48" />
				</div>
			{/if}
			{#if failed && report.error}
				<p class="flex items-start gap-1.5 pt-1 text-xs text-destructive">
					<TriangleAlertIcon class="mt-px size-3.5 shrink-0" />
					<span class="break-words">{report.error}</span>
				</p>
			{/if}
		</div>

		<div class="flex shrink-0 items-center gap-1.5">
			{#if previewable}
				<Button variant="outline" size="sm" onclick={() => (previewOpen = true)}>
					<EyeIcon class="size-3.5" />
					Preview
				</Button>
			{:else if report.files.length}
				{@const Icon = FORMAT_ICONS[primary.format]}
				<Button
					variant="outline"
					size="sm"
					href={reportsApi.downloadUrl(projectId, report.id, primary.format)}
					download
				>
					<Icon class="size-3.5" />
					{FORMAT_LABELS[primary.format]}
					<span class="text-muted-foreground">{formatBytes(primary.bytes)}</span>
				</Button>
			{/if}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							variant="ghost"
							size="icon"
							class="size-7"
							{...props}
							aria-label="Actions for {report.title}"
						>
							<EllipsisIcon class="size-4" />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-52">
					{#each report.files as file (file.format)}
						{@const Icon = FORMAT_ICONS[file.format]}
						<DropdownMenu.Item>
							{#snippet child({ props })}
								<a
									{...props}
									href={reportsApi.downloadUrl(projectId, report.id, file.format)}
									download
								>
									<Icon class="size-4" />
									Download {FORMAT_LABELS[file.format]}
									<span class="ml-auto text-xs text-muted-foreground"
										>{formatBytes(file.bytes)}</span
									>
								</a>
							{/snippet}
						</DropdownMenu.Item>
					{/each}
					{#if report.files.length}<DropdownMenu.Separator />{/if}
					<DropdownMenu.Item onSelect={() => onRetry(report.id)} disabled={live}>
						<RefreshCwIcon class="size-4" />
						Generate again
					</DropdownMenu.Item>
					<DropdownMenu.Separator />
					<DropdownMenu.Item variant="destructive" onSelect={() => onDelete(report.id)}>
						<Trash2Icon class="size-4" />
						Delete
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>
</div>

{#if previewable}
	<ReportPreviewDialog bind:open={previewOpen} {report} {projectId} />
{/if}
