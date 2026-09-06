<script lang="ts">
	import Play from '@lucide/svelte/icons/play';
	import Ban from '@lucide/svelte/icons/ban';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Copy from '@lucide/svelte/icons/copy';
	import Globe from '@lucide/svelte/icons/globe';
	import FileBracesCorner from '@lucide/svelte/icons/file-braces-corner';
	import FileSpreadsheet from '@lucide/svelte/icons/file-spreadsheet';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { toast } from 'svelte-sonner';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Spinner } from '$lib/components/ui/spinner';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import CopyButton from '$lib/components/copy-button.svelte';
	import TargetOrgPopover from '$lib/components/targets/target-org-popover.svelte';
	import TargetTagPopover from '$lib/components/targets/target-tag-popover.svelte';
	import { TARGET_TYPE_ICONS } from '$lib/config/icons';
	import { targetTypeLabel } from '$lib/types/scan-engine';
	import { TargetType, type Target } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import { getFreshnessLevel, formatShortDate } from '$lib/utilities/dates';
	import { getExternalLinksTargetDropdown } from '$lib/utilities/target-detail-external-links';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import FileText from '@lucide/svelte/icons/file-text';
	import { ROUTES } from '$lib/config/routes';

	interface Props {
		target: Target;
		creator: string | null;
		live?: boolean;
		onScan: () => void;
		onCancel?: () => void;
		onRefreshEnrichment: () => void;
		onExportJson: () => void;
		onExportCsv: () => void;
		onDelete: () => void;
		onReport: () => void;
		onChange: (patch: Partial<Target>) => void;
	}

	let {
		target,
		creator,
		live = false,
		onScan,
		onCancel,
		onRefreshEnrichment,
		onExportJson,
		onExportCsv,
		onDelete,
		onReport,
		onChange
	}: Props = $props();

	const TargetIcon = $derived(TARGET_TYPE_ICONS[target.target_type] ?? Globe);
	const externalLinks = $derived(
		getExternalLinksTargetDropdown(target.target_value, target.target_type)
	);

	interface Source {
		label: string;
		status: TaskStatus;
		queriedAt: string | null;
	}
	const sources = $derived.by<Source[]>(() => {
		const t = target.target_type;
		const out: Source[] = [];
		if (t === TargetType.DOMAIN || t === TargetType.URL)
			out.push({
				label: 'DNS',
				status: target.dns_status,
				queriedAt: target.dns?.queried_at ?? null
			});
		out.push({
			label: 'WHOIS',
			status: target.whois_status,
			queriedAt: target.whois?.queried_at ?? null
		});
		if (t === TargetType.IP || t === TargetType.IP_RANGE || t === TargetType.ASN)
			out.push({
				label: 'BGP',
				status: target.bgp_status,
				queriedAt: target.bgp?.queried_at ?? null
			});
		return out;
	});
	const pendingSources = $derived(
		sources.filter((s) => s.status === TaskStatus.PENDING || s.status === TaskStatus.QUERYING)
	);
	const failedSources = $derived(sources.filter((s) => s.status === TaskStatus.FAILED));
	const lastEnrichedAt = $derived.by(() => {
		const times = sources
			.filter((s) => s.status === TaskStatus.SUCCESS && s.queriedAt)
			.map((s) => new Date(s.queriedAt!).getTime());
		return times.length ? new Date(Math.max(...times)).toISOString() : null;
	});
	const stale = $derived(getFreshnessLevel(lastEnrichedAt) === 'stale');

	async function copyValue() {
		if (await writeClipboard(target.target_value)) toast.success('Copied');
	}
	async function copyId() {
		if (await writeClipboard(target.id)) toast.success('Target ID copied');
	}
</script>

<header class="flex flex-wrap items-start justify-between gap-4">
	<div class="flex min-w-0 items-start gap-3">
		<div
			class="flex size-10 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/40"
		>
			<TargetIcon class="size-5 text-muted-foreground" />
		</div>
		<div class="flex min-w-0 flex-col gap-1.5">
			<div class="flex flex-wrap items-center gap-2">
				<h1 class="truncate font-mono text-xl font-medium">{target.target_value}</h1>
				<Badge variant="outline" class="font-normal text-muted-foreground">
					{targetTypeLabel(target.target_type)}
				</Badge>
				<CopyButton value={target.target_value} />
			</div>
			<div class="flex flex-wrap items-center gap-x-2 gap-y-1.5 text-sm text-muted-foreground">
				{#if target.display_name && target.display_name !== target.target_value}
					<span class="text-foreground">{target.display_name}</span>
					<span aria-hidden="true">·</span>
				{/if}
				<span>Added {formatShortDate(target.created_at)}{creator ? ` by ${creator}` : ''}</span>
				<span aria-hidden="true">·</span>
				<TargetOrgPopover
					targetId={target.id}
					currentOrgs={target.organizations}
					maxVisible={3}
					{onChange}
				/>
				<TargetTagPopover
					targetId={target.id}
					currentTags={target.tags}
					maxVisible={4}
					{onChange}
				/>
				{#if pendingSources.length || failedSources.length}
					<span aria-hidden="true">·</span>
				{/if}
				{#if pendingSources.length}
					<span class="flex items-center gap-1.5 text-info">
						<Spinner class="size-3" />
						Collecting {pendingSources.map((s) => s.label).join(', ')}
					</span>
				{:else if stale}
					<Badge variant="warning" class="h-5 px-1.5 text-[11px]">Enrichment stale</Badge>
				{/if}
				{#each failedSources as s (s.label)}
					<Badge variant="destructive" class="h-5 gap-1 px-1.5 text-[11px]">
						<TriangleAlert class="size-3" />
						{s.label} failed
					</Badge>
				{/each}
			</div>
		</div>
	</div>

	<div class="flex items-center gap-2">
		{#if live && onCancel}
			<Button variant="outline" size="sm" class="gap-1.5" onclick={onCancel}>
				<Ban class="size-3.5" />
				Cancel
			</Button>
		{:else}
			<Button variant="outline" size="sm" class="gap-1.5" onclick={onReport}>
				<FileText class="size-3.5" />
				Report
			</Button>
			<Button size="sm" class="gap-1.5" onclick={onScan}>
				<Play class="size-3.5" />
				Scan
			</Button>
		{/if}
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button {...props} variant="outline" size="icon-sm" aria-label="More actions">
						<Ellipsis class="size-4" />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="w-56">
				<DropdownMenu.Item onclick={onRefreshEnrichment} disabled={pendingSources.length > 0}>
					<RefreshCw class="size-4" />
					Refresh enrichment
				</DropdownMenu.Item>
				<DropdownMenu.Item onclick={copyValue}>
					<Copy class="size-4" />
					Copy target
				</DropdownMenu.Item>
				<DropdownMenu.Item onclick={copyId}>
					<Copy class="size-4" />
					Copy target ID
				</DropdownMenu.Item>
				<DropdownMenu.Item>
					{#snippet child({ props })}
						<a {...props} href={ROUTES.reportsForTarget(target.id)}>
							<FileText class="size-4" />
							Reports for this target
						</a>
					{/snippet}
				</DropdownMenu.Item>
				<DropdownMenu.Separator />
				<DropdownMenu.Label>Export</DropdownMenu.Label>
				<DropdownMenu.Item onclick={onExportJson}>
					<FileBracesCorner class="size-4" />
					Export as JSON
				</DropdownMenu.Item>
				<DropdownMenu.Item onclick={onExportCsv}>
					<FileSpreadsheet class="size-4" />
					Export as CSV
				</DropdownMenu.Item>
				{#if externalLinks.length > 0}
					<DropdownMenu.Separator />
					<DropdownMenu.Label>External lookup</DropdownMenu.Label>
					{#each externalLinks as link (link.url)}
						<DropdownMenu.Item>
							{#snippet child({ props })}
								<a {...props} href={link.url} target="_blank" rel="noopener noreferrer">
									<ExternalLink class="size-4" />
									{link.label}
								</a>
							{/snippet}
						</DropdownMenu.Item>
					{/each}
				{/if}
				<DropdownMenu.Separator />
				<DropdownMenu.Item class="text-destructive focus:text-destructive" onclick={onDelete}>
					<Trash2 class="size-4" />
					Delete target
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>
</header>
