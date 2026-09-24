<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Download from '@lucide/svelte/icons/download';
	import FilePlus from '@lucide/svelte/icons/file-plus';
	import FileCode from '@lucide/svelte/icons/file-code';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Upload from '@lucide/svelte/icons/upload';
	import * as Card from '$lib/components/ui/card';
	import * as Select from '$lib/components/ui/select';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Switch } from '$lib/components/ui/switch';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import SeverityBar from '$lib/components/scans/results/vulnerabilities/severity-bar.svelte';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import TemplateSheet from './template-sheet.svelte';
	import { vulnTemplatesApi } from '$lib/api/vulnerabilities';
	import SelectionDeleteBar from '$lib/components/selection-delete-bar.svelte';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { SvelteSet } from 'svelte/reactivity';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		MAX_TEMPLATE_UPLOAD,
		PROTOCOL_LABELS,
		SEVERITY_FILL,
		SEVERITY_LABELS,
		SEVERITY_ORDER,
		TEMPLATE_ORIGIN_LABELS,
		TEMPLATE_SET_ICONS,
		TEMPLATE_SET_LABELS
	} from '$lib/config/vulnerabilities';
	import { emptyTemplateFilter } from '$lib/types/vuln-template';
	import type {
		TemplateFilter,
		TemplateLibraryStats,
		VulnTemplateRead
	} from '$lib/types/vuln-template';
	import { afterPause } from '$lib/utilities/debounce';

	const PAGE_SIZE = 25;
	const ALL = 'all';

	let stats = $state<TemplateLibraryStats | null>(null);
	let statsLoading = $state(true);
	let statsError = $state<string | null>(null);
	let items = $state<VulnTemplateRead[]>([]);
	let total = $state(0);
	let listLoading = $state(true);
	let listError = $state<string | null>(null);
	let syncing = $state(false);
	let uploading = $state(false);
	let removing = $state<VulnTemplateRead | null>(null);
	let viewing = $state<VulnTemplateRead | null>(null);
	let creating = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);
	let filter = $state<TemplateFilter>({ ...emptyTemplateFilter(), limit: PAGE_SIZE });
	let search = $state('');
	let severity = $state(ALL);
	let origin = $state(ALL);
	let set = $state(ALL);
	let onlyNew = $state(false);
	let seenAt = $state<string | null>(null);
	let reqId = 0;

	let newCount = $state(0);

	function isNew(template: VulnTemplateRead): boolean {
		return (
			seenAt !== null &&
			template.origin === 'official' &&
			Date.parse(template.created_at) > Date.parse(seenAt)
		);
	}

	let pageCount = $derived(Math.max(1, Math.ceil(total / PAGE_SIZE)));
	let pageIndex = $derived(Math.floor(filter.offset / PAGE_SIZE));
	let sets = $derived(stats?.sets ?? []);
	let severityCounts = $derived(
		(stats?.by_severity ?? []).map((part) => ({
			severity: part.key,
			label: part.label,
			count: part.count
		}))
	);

	function tileStyle(severity: string) {
		const fill = SEVERITY_FILL[severity] ?? SEVERITY_FILL.unknown;
		return `background:color-mix(in oklch, ${fill} 14%, transparent);color:color-mix(in oklch, ${fill} 85%, var(--foreground));box-shadow:inset 0 0 0 1px color-mix(in oklch, ${fill} 30%, transparent)`;
	}

	let marked = false;

	async function loadStats() {
		statsLoading = true;
		try {
			stats = await vulnTemplatesApi.stats();
			statsError = null;
			if (!marked) {
				marked = true;
				seenAt = stats.seen_at;
				newCount = stats.new;
				void vulnTemplatesApi.seen().catch(() => undefined);
			}
		} catch (e) {
			stats = null;
			statsError = e instanceof Error ? e.message : 'Request failed.';
		} finally {
			statsLoading = false;
		}
	}

	async function loadList() {
		const my = ++reqId;
		listLoading = true;
		try {
			const res = await vulnTemplatesApi.search(filter);
			if (my !== reqId) return;
			items = res.items;
			total = res.total;
			listError = null;
		} catch (e) {
			if (my === reqId) {
				items = [];
				total = 0;
				listError = e instanceof Error ? e.message : 'Request failed.';
			}
		} finally {
			if (my === reqId) listLoading = false;
		}
	}

	$effect(() => {
		untrack(() => {
			void loadStats();
		});
	});

	$effect(() => {
		void JSON.stringify(filter);
		return afterPause(loadList);
	});

	$effect(() => {
		const q = search.trim() || null;
		const sev = severity === ALL ? [] : [severity];
		const org = origin === ALL ? [] : [origin];
		const chosen = set === ALL ? [] : [set];
		const newSince = onlyNew ? seenAt : null;
		untrack(() => {
			filter = {
				...filter,
				q,
				severities: sev,
				origins: org,
				sets: chosen,
				new_since: newSince,
				offset: 0
			};
		});
	});

	async function sync() {
		syncing = true;
		try {
			const res = await vulnTemplatesApi.sync();
			if (res.started) toast.success('Library sync started', { description: res.message });
			else toast.error(res.message);
		} catch {
			toast.error('Library sync not started');
		} finally {
			syncing = false;
		}
	}

	async function upload(event: Event) {
		const input = event.target as HTMLInputElement;
		const chosen = [...(input.files ?? [])].slice(0, MAX_TEMPLATE_UPLOAD);
		if (!chosen.length) return;
		uploading = true;
		try {
			const files = await Promise.all(
				chosen.map(async (file) => ({ filename: file.name, content: await file.text() }))
			);
			const res = await vulnTemplatesApi.upload(files);
			const accepted = res.accepted.length;
			if (accepted) {
				toast.success(
					`${accepted} ${accepted === 1 ? 'check' : 'checks'} added`,
					res.replaced
						? {
								description: `${res.replaced} existing ${res.replaced === 1 ? 'check' : 'checks'} replaced`
							}
						: undefined
				);
			}
			for (const rejection of res.rejected) {
				toast.error(`${rejection.filename} not added`, { description: rejection.reason });
			}
			await Promise.all([loadStats(), loadList()]);
		} catch {
			toast.error('Checks not uploaded');
		} finally {
			uploading = false;
			input.value = '';
		}
	}

	async function toggle(template: VulnTemplateRead, enabled: boolean) {
		try {
			const updated = await vulnTemplatesApi.update(template.id, enabled);
			items = items.map((t) => (t.id === updated.id ? updated : t));
		} catch {
			toast.error('Check not updated');
		}
	}

	const picked = new SvelteSet<string>();

	function toggleCheck(id: string) {
		if (picked.has(id)) picked.delete(id);
		else picked.add(id);
	}

	async function remove() {
		const target = removing;
		if (!target) return;
		try {
			await vulnTemplatesApi.remove(target.id);
			toast.success(`${target.name} removed`);
			removing = null;
			await Promise.all([loadStats(), loadList()]);
		} catch {
			toast.error('Check not removed');
		}
	}

	function page(next: number) {
		filter = { ...filter, offset: Math.max(0, next) * PAGE_SIZE };
	}
</script>

<Card.Root class="gap-0 py-0">
	<Card.Header class="border-b py-5">
		<Card.Title>Check library</Card.Title>
		{#if stats?.last_synced_at}
			<Card.Description>Synced {relativeTime(stats.last_synced_at)}</Card.Description>
		{/if}
		<Card.Action class="flex items-center gap-2">
			<input
				bind:this={fileInput}
				type="file"
				accept=".yaml,.yml"
				multiple
				class="hidden"
				onchange={upload}
			/>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<LoadingButton
							{...props}
							variant="outline"
							size="sm"
							class="gap-2"
							loading={uploading}
							loadingLabel="Uploading"
						>
							<Plus class="size-4" /> Add check
							<ChevronDown class="size-3.5 text-muted-foreground" />
						</LoadingButton>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end">
					<DropdownMenu.Item onclick={() => (creating = true)}>
						<FilePlus class="size-4" /> New check
					</DropdownMenu.Item>
					<DropdownMenu.Item onclick={() => fileInput?.click()}>
						<Upload class="size-4" /> Upload checks
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
			<LoadingButton
				size="sm"
				class="gap-2"
				loading={syncing}
				loadingLabel="Syncing"
				onclick={sync}
			>
				<Download class="size-4" /> Sync library
			</LoadingButton>
		</Card.Action>
	</Card.Header>

	<div class="border-b px-6 py-4">
		{#if statsLoading}
			<Skeleton class="h-12 w-full" />
		{:else if statsError}
			<div class="flex items-start gap-3">
				<TriangleAlert class="mt-0.5 size-4 shrink-0 text-destructive" />
				<div class="flex flex-col gap-0.5">
					<p class="text-sm font-medium">Library not loaded</p>
					<p class="text-xs text-muted-foreground">{statsError}</p>
				</div>
			</div>
		{:else if !stats?.ready}
			<div class="flex items-start gap-3">
				<TriangleAlert class="mt-0.5 size-4 shrink-0 text-warning" />
				<div class="flex flex-col gap-0.5">
					<p class="text-sm font-medium">No checks</p>
					<p class="text-xs text-muted-foreground">Sync the library.</p>
				</div>
			</div>
		{:else}
			<div class="flex flex-wrap items-end gap-x-10 gap-y-4">
				<div class="flex flex-col">
					<span class="font-mono text-2xl leading-8 font-semibold tabular-nums">
						{stats.total.toLocaleString()}
					</span>
					<span class="text-xs text-muted-foreground">checks</span>
				</div>
				<div class="flex flex-col">
					<span class="font-mono text-sm leading-6 tabular-nums">
						{stats.official.toLocaleString()}
					</span>
					<span class="text-xs text-muted-foreground">{TEMPLATE_ORIGIN_LABELS.official}</span>
				</div>
				<div class="flex flex-col">
					<span class="font-mono text-sm leading-6 tabular-nums">
						{stats.custom.toLocaleString()}
					</span>
					<span class="text-xs text-muted-foreground">{TEMPLATE_ORIGIN_LABELS.custom}</span>
				</div>
				<div class="flex min-w-64 flex-1 flex-col gap-2">
					<SeverityBar counts={severityCounts} height="h-1.5" />
					<div class="flex flex-wrap gap-x-4 gap-y-1">
						{#each stats.by_severity as part (part.key)}
							<span class="flex items-center gap-1.5 text-xs">
								<SeverityMark severity={part.key} showLabel={false} />
								<span class="text-muted-foreground">{part.label}</span>
								<span class="font-mono tabular-nums">{part.count.toLocaleString()}</span>
							</span>
						{/each}
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex flex-wrap items-center gap-2 border-b px-6 py-3">
		<Input
			bind:value={search}
			placeholder="Search checks by name or identifier"
			class="h-9 w-full sm:max-w-xs"
		/>
		<Select.Root type="single" bind:value={severity}>
			<Select.Trigger class="h-9 w-36">
				{severity === ALL ? 'Any severity' : SEVERITY_LABELS[severity]}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value={ALL} label="Any severity">Any severity</Select.Item>
				{#each SEVERITY_ORDER as value (value)}
					<Select.Item {value} label={SEVERITY_LABELS[value]}>
						{SEVERITY_LABELS[value]}
					</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		<Select.Root type="single" bind:value={set}>
			<Select.Trigger class="h-9 w-44">
				{set === ALL ? 'Any check set' : (sets.find((s) => s.key === set)?.label ?? set)}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value={ALL} label="Any check set">Any check set</Select.Item>
				{#each sets as spec (spec.key)}
					<Select.Item value={spec.key} label={spec.label}>
						{spec.label}
						<span class="ml-auto text-xs text-muted-foreground tabular-nums">
							{spec.count.toLocaleString()}
						</span>
					</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		<Select.Root type="single" bind:value={origin}>
			<Select.Trigger class="h-9 w-40">
				{origin === ALL ? 'Any origin' : TEMPLATE_ORIGIN_LABELS[origin]}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value={ALL} label="Any origin">Any origin</Select.Item>
				{#each Object.entries(TEMPLATE_ORIGIN_LABELS) as [value, label] (value)}
					<Select.Item {value} {label}>{label}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		{#if newCount > 0}
			<ToggleGroup.Root
				type="single"
				value={onlyNew ? 'new' : ''}
				onValueChange={(v) => (onlyNew = v === 'new')}
				variant="outline"
				aria-label="New checks"
			>
				<ToggleGroup.Item value="new" class="h-9 gap-1.5 px-3 text-sm font-normal">
					New
					<span class="text-info tabular-nums">{newCount.toLocaleString()}</span>
				</ToggleGroup.Item>
			</ToggleGroup.Root>
		{/if}
		<Button
			variant="outline"
			size="icon"
			class="ml-auto h-9 w-9"
			aria-label="Refresh"
			onclick={() => {
				void loadStats();
				void loadList();
			}}
		>
			<RefreshCw class="size-4 {listLoading ? 'animate-spin' : ''}" />
		</Button>
	</div>

	{#if listLoading && items.length === 0}
		<div class="divide-y">
			{#each Array(6) as _, i (i)}
				<div class="px-6 py-3"><Skeleton class="h-9 w-full" /></div>
			{/each}
		</div>
	{:else if listError}
		<EmptyState
			icon={TriangleAlert}
			title="Checks not loaded"
			description={listError}
			class="rounded-none border-0 bg-transparent py-12"
		>
			<Button variant="outline" size="sm" onclick={() => void loadList()}>Retry</Button>
		</EmptyState>
	{:else if items.length === 0}
		<EmptyState
			icon={SearchX}
			title="No checks match"
			class="rounded-none border-0 bg-transparent py-12"
		/>
	{:else}
		<div class="divide-y">
			{#each items as template (template.id)}
				{@const custom = template.origin === 'custom'}
				{@const SetIcon = TEMPLATE_SET_ICONS[template.sets[0] ?? ''] ?? FileCode}
				<div class="flex items-start gap-3 px-6 py-3 hover:bg-muted/40">
					{#if custom}
						<span class="flex h-7 shrink-0 items-center">
							<Checkbox
								checked={picked.has(template.id)}
								onCheckedChange={() => toggleCheck(template.id)}
								aria-label="Select {template.name}"
							/>
						</span>
					{:else}
						<span class="w-4 shrink-0"></span>
					{/if}
					<span
						class="flex size-7 shrink-0 items-center justify-center rounded-md"
						style={tileStyle(template.severity)}
					>
						<SetIcon class="size-4" />
					</span>
					<div class="flex min-w-0 flex-1 flex-col gap-1">
						<div class="flex flex-wrap items-center gap-2">
							<span class="text-sm leading-5 font-medium wrap-anywhere">
								{template.name}
							</span>
							{#if custom}
								<Badge variant="info" class="text-2xs font-normal">Custom</Badge>
							{/if}
							{#if isNew(template)}
								<Hint text={`Added ${relativeTime(template.created_at)}`}>
									{#snippet child(props)}
										<span {...props} class="flex h-5 items-center">
											<Badge variant="info" class="px-1.5 text-2xs font-normal">New</Badge>
										</span>
									{/snippet}
								</Hint>
							{/if}
						</div>
						<div
							class="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground"
						>
							<SeverityMark severity={template.severity} />
							<span class="font-mono">{template.template_id}</span>
							{#each template.sets.slice(0, 2) as key (key)}
								<span>{TEMPLATE_SET_LABELS[key] ?? key}</span>
							{/each}
							<span>{PROTOCOL_LABELS[template.protocol] ?? template.protocol}</span>
							{#each template.cve_ids.slice(0, 1) as cve (cve)}
								<span class="font-mono">{cve}</span>
							{/each}
							{#if template.requests}
								<span>
									{template.requests}
									{template.requests === 1 ? 'request' : 'requests'}
								</span>
							{/if}
						</div>
					</div>
					<div class="flex shrink-0 items-center gap-2">
						<Button
							variant="ghost"
							size="icon"
							class="size-8 text-muted-foreground hover:text-foreground"
							aria-label="{custom ? 'Edit' : 'View'} {template.name}"
							onclick={() => (viewing = template)}
						>
							<FileCode class="size-4" />
						</Button>
						<Switch
							checked={template.enabled}
							onCheckedChange={(value) => toggle(template, value)}
							aria-label="Enable {template.name}"
						/>
						{#if custom}
							<Button
								variant="ghost"
								size="icon"
								class="size-8 text-muted-foreground hover:text-destructive"
								aria-label="Remove {template.name}"
								onclick={() => (removing = template)}
							>
								<Trash2 class="size-4" />
							</Button>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}

	{#if total > PAGE_SIZE}
		<div class="flex items-center justify-between border-t px-6 py-2.5 text-xs">
			<span class="text-muted-foreground tabular-nums">
				{(pageIndex * PAGE_SIZE + 1).toLocaleString()}–{Math.min(
					(pageIndex + 1) * PAGE_SIZE,
					total
				).toLocaleString()} of {total.toLocaleString()}
			</span>
			<div class="flex items-center gap-2">
				<Button
					variant="outline"
					size="sm"
					class="h-7"
					disabled={pageIndex === 0}
					onclick={() => page(pageIndex - 1)}
				>
					Previous
				</Button>
				<Button
					variant="outline"
					size="sm"
					class="h-7"
					disabled={pageIndex >= pageCount - 1}
					onclick={() => page(pageIndex + 1)}
				>
					Next
				</Button>
			</div>
		</div>
	{/if}
</Card.Root>

<TemplateSheet
	template={viewing}
	{creating}
	onOpenChange={(value) => {
		if (!value) {
			viewing = null;
			creating = false;
		}
	}}
	onSaved={() => {
		void loadStats();
		void loadList();
	}}
/>

<DeleteConfirmationDialog
	open={!!removing}
	onOpenChange={(value) => {
		if (!value) removing = null;
	}}
	title="Remove check"
	description={`Check ${removing?.name ?? ''} and its file are removed.`}
	confirmLabel="Remove"
	onConfirm={remove}
/>

<SelectionDeleteBar
	ids={[...picked]}
	noun="check"
	removes="files"
	remove={(id) => vulnTemplatesApi.remove(id)}
	onDone={async () => {
		picked.clear();
		await Promise.all([loadStats(), loadList()]);
	}}
	onClear={() => picked.clear()}
/>
