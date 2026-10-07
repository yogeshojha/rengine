<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { browser } from '$app/environment';
	import { page as route } from '$app/state';
	import { replaceState } from '$app/navigation';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Download from '@lucide/svelte/icons/download';
	import FilePlus from '@lucide/svelte/icons/file-plus';
	import FileCode from '@lucide/svelte/icons/file-code';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import SearchX from '@lucide/svelte/icons/search-x';
	import Search from '@lucide/svelte/icons/search';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Upload from '@lucide/svelte/icons/upload';
	import X from '@lucide/svelte/icons/x';
	import * as Card from '$lib/components/ui/card';
	import * as Select from '$lib/components/ui/select';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as InputGroup from '$lib/components/ui/input-group';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Switch } from '$lib/components/ui/switch';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import RowSkeleton from '$lib/components/skeleton/row-skeleton.svelte';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import SeverityBar from '$lib/components/scans/results/vulnerabilities/severity-bar.svelte';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import TemplateSheet from './template-sheet.svelte';
	import CallbackServerSheet from './callback-server-sheet.svelte';
	import { oastApi } from '$lib/api/oast';
	import { CALLBACK_PANEL, PANEL_PARAM } from '$lib/config/routes';
	import { CALLBACK_SERVER, OAST_MODE_LABELS, OastMode } from '$lib/config/oast';
	import type { OastRead } from '$lib/types/oast';
	import { vulnTemplatesApi } from '$lib/api/vulnerabilities';
	import { auth } from '$lib/stores/auth.svelte';
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
		TEMPLATE_SET_LABELS,
		TemplateOrigin
	} from '$lib/config/vulnerabilities';
	import { emptyTemplateFilter } from '$lib/types/vuln-template';
	import type {
		TemplateFilter,
		TemplateLibraryStats,
		VulnTemplateRead
	} from '$lib/types/vuln-template';
	import { afterPause } from '$lib/utilities/debounce';

	let { active = true }: { active?: boolean } = $props();

	const PAGE_SIZE = 25;
	const ALL = 'all';

	interface Criteria {
		search: string;
		severity: string;
		origin: string;
		set: string;
		onlyNew: boolean;
		onlyCallback: boolean;
	}

	function markFrom(params: URLSearchParams): string | null {
		const value = params.get('new');
		return value && !Number.isNaN(Date.parse(value)) ? value : null;
	}

	function criteriaFrom(params: URLSearchParams): Criteria {
		const severity = params.get('severity') ?? ALL;
		const origin = params.get('origin') ?? ALL;
		return {
			search: params.get('q') ?? '',
			severity: SEVERITY_ORDER.includes(severity) ? severity : ALL,
			origin: Object.hasOwn(TEMPLATE_ORIGIN_LABELS, origin) ? origin : ALL,
			set: params.get('set') || ALL,
			onlyNew: markFrom(params) !== null,
			onlyCallback: params.get('callback') === '1'
		};
	}

	function criteriaFilter(c: Criteria) {
		return {
			q: c.search.trim() || null,
			severities: c.severity === ALL ? [] : [c.severity],
			origins: c.origin === ALL ? [] : [c.origin],
			sets: c.set === ALL ? [] : [c.set],
			callback: c.onlyCallback
		};
	}

	function criteriaKey(c: Criteria): string {
		return JSON.stringify({ ...criteriaFilter(c), onlyNew: c.onlyNew });
	}

	const landed = untrack(() => active)
		? new URLSearchParams(browser ? location.search : route.url.search)
		: new URLSearchParams();
	const landedCriteria = criteriaFrom(landed);
	const landedMark = markFrom(landed);
	const landedPage = Number.parseInt(landed.get('page') ?? '', 10);
	let appliedKey = criteriaKey(landedCriteria);

	const isAdmin = $derived(auth.user?.is_superuser ?? false);

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
	let deleting = $state(false);
	let viewing = $state<VulnTemplateRead | null>(null);
	let creating = $state(false);
	let fileInput = $state<HTMLInputElement | null>(null);
	let filter = $state<TemplateFilter>({
		...emptyTemplateFilter(),
		...criteriaFilter(landedCriteria),
		limit: PAGE_SIZE,
		offset: landedPage > 1 ? (landedPage - 1) * PAGE_SIZE : 0
	});
	let search = $state(landedCriteria.search);
	let severity = $state(landedCriteria.severity);
	let origin = $state(landedCriteria.origin);
	let set = $state(landedCriteria.set);
	let onlyNew = $state(landedCriteria.onlyNew);
	let onlyCallback = $state(landedCriteria.onlyCallback);
	let oast = $state<OastRead | null>(null);
	let oastFailed = $state(false);
	let callbackOpen = $state(false);
	let seenAt = $state<string | null>(landedMark);
	let reqId = 0;

	let newCount = $state(0);

	function isNew(template: VulnTemplateRead): boolean {
		return (
			seenAt !== null &&
			template.origin === TemplateOrigin.OFFICIAL &&
			Date.parse(template.created_at) > Date.parse(seenAt)
		);
	}

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

	async function countSince(mark: string): Promise<number> {
		try {
			const page = await vulnTemplatesApi.search({
				...emptyTemplateFilter(),
				new_since: mark,
				limit: 1
			});
			return page.total;
		} catch {
			return 0;
		}
	}

	async function loadStats() {
		statsLoading = true;
		try {
			stats = await vulnTemplatesApi.stats();
			statsError = null;
			if (!marked) {
				marked = true;
				seenAt = landedMark ?? stats.seen_at;
				newCount = landedMark ? await countSince(landedMark) : stats.new;
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
		const next: Criteria = { search, severity, origin, set, onlyNew, onlyCallback };
		const newSince = onlyNew ? seenAt : null;
		untrack(() => {
			const key = criteriaKey(next);
			const changed = key !== appliedKey;
			if (!changed && filter.new_since === newSince) return;
			appliedKey = key;
			filter = {
				...filter,
				...criteriaFilter(next),
				new_since: newSince,
				offset: changed ? 0 : filter.offset
			};
		});
	});

	$effect(() => {
		const values: [string, string][] = [
			['q', search.trim()],
			['severity', severity === ALL ? '' : severity],
			['set', set === ALL ? '' : set],
			['origin', origin === ALL ? '' : origin],
			['new', onlyNew && seenAt ? seenAt : ''],
			['callback', onlyCallback ? '1' : ''],
			['page', pageIndex > 0 ? String(pageIndex + 1) : '']
		];
		const shown = active;
		void route.url;
		if (!browser) return;
		untrack(() => {
			const url = new URL(location.href);
			for (const [key, value] of values) {
				if (shown && value) url.searchParams.set(key, value);
				else url.searchParams.delete(key);
			}
			if (url.search === location.search) return;
			try {
				replaceState(url, {});
			} catch {}
		});
	});

	const callbackState = $derived(
		!oast || oast.mode === OastMode.OFF ? 'off' : oast.reason ? 'blocked' : 'on'
	);
	const CALLBACK_DOT: Record<string, string> = {
		on: 'bg-success',
		blocked: 'bg-warning',
		off: 'bg-muted-foreground/40'
	};

	function loadOast() {
		oastFailed = false;
		void oastApi
			.get()
			.then((row) => (oast = row))
			.catch(() => {
				oast = null;
				oastFailed = true;
			});
	}

	onMount(() => {
		loadOast();
	});

	$effect(() => {
		if (route.url.searchParams.get(PANEL_PARAM) === CALLBACK_PANEL)
			untrack(() => (callbackOpen = true));
	});

	$effect(() => {
		if (callbackOpen) return;
		const params = untrack(() => new URLSearchParams(location.search));
		if (params.get(PANEL_PARAM) !== CALLBACK_PANEL) return;
		params.delete(PANEL_PARAM);
		const qs = params.toString();
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {}
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
		const chosen = [...(input.files ?? [])];
		if (chosen.length > MAX_TEMPLATE_UPLOAD) {
			toast.error(
				`${chosen.length} files selected. The limit is ${MAX_TEMPLATE_UPLOAD} per upload.`
			);
			input.value = '';
			return;
		}
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
		deleting = true;
		try {
			await vulnTemplatesApi.remove(target.id);
			picked.delete(target.id);
			toast.success(`${target.name} deleted`);
			removing = null;
			await Promise.all([loadStats(), loadList()]);
		} catch {
			toast.error('Check not deleted');
		} finally {
			deleting = false;
		}
	}

	function page(next: number) {
		filter = { ...filter, offset: Math.max(0, next) * PAGE_SIZE };
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<Card.Header class="border-b px-4 py-5">
		<Card.Title>Check library</Card.Title>
		{#if stats?.last_synced_at}
			<Card.Description>Synced {relativeTime(stats.last_synced_at)}</Card.Description>
		{/if}
		<Card.Action class="flex flex-wrap items-center justify-end gap-2">
			<Button variant="outline" size="sm" onclick={() => (callbackOpen = true)}>
				<span class="size-2 shrink-0 rounded-full {CALLBACK_DOT[callbackState]}" aria-hidden="true"
				></span>
				{CALLBACK_SERVER}
				<span class="text-muted-foreground">
					{callbackState === 'on' && oast ? OAST_MODE_LABELS[oast.mode as OastMode] : 'Off'}
				</span>
			</Button>
			<input
				bind:this={fileInput}
				type="file"
				accept=".yaml,.yml"
				multiple
				class="hidden"
				onchange={upload}
			/>
			<Hint text={isAdmin ? null : 'Editable by administrators'}>
				{#snippet child(hintProps)}
					<span {...hintProps} class="inline-flex">
						<DropdownMenu.Root>
							<DropdownMenu.Trigger>
								{#snippet child({ props })}
									<LoadingButton
										{...props}
										variant="outline"
										size="sm"
										loading={uploading}
										loadingLabel="Uploading"
										disabled={!isAdmin}
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
					</span>
				{/snippet}
			</Hint>
			<Hint text={isAdmin ? null : 'Editable by administrators'}>
				{#snippet child(props)}
					<span {...props} class="inline-flex">
						<LoadingButton
							size="sm"
							loading={syncing}
							loadingLabel="Syncing"
							disabled={!isAdmin}
							onclick={sync}
						>
							<Download class="size-4" /> Sync library
						</LoadingButton>
					</span>
				{/snippet}
			</Hint>
		</Card.Action>
	</Card.Header>

	<div class="border-b px-4 py-4">
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
				<p class="text-sm font-medium">No checks</p>
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
				{#if stats.callback > 0}
					<button
						type="button"
						class="-mx-2 -my-1 flex flex-col rounded-md px-2 py-1 text-left transition-colors outline-none hover:bg-muted/60 focus-visible:ring-[3px] focus-visible:ring-ring/50 aria-pressed:bg-muted"
						aria-pressed={onlyCallback}
						onclick={() => (onlyCallback = !onlyCallback)}
					>
						<span class="font-mono text-sm leading-6 tabular-nums">
							{stats.callback.toLocaleString()}
						</span>
						<span class="text-xs text-muted-foreground">Need a callback</span>
					</button>
				{/if}
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

	<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
		<InputGroup.Root class="w-full sm:max-w-xs">
			<InputGroup.Addon><Search /></InputGroup.Addon>
			<InputGroup.Input
				bind:value={search}
				placeholder="Search checks by name or identifier"
				aria-label="Search checks"
			/>
		</InputGroup.Root>
		<Select.Root type="single" bind:value={severity}>
			<Select.Trigger class="w-36" aria-label="Severity">
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
			<Select.Trigger class="w-44" aria-label="Check set">
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
			<Select.Trigger class="w-40" aria-label="Origin">
				{origin === ALL ? 'Any origin' : TEMPLATE_ORIGIN_LABELS[origin]}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value={ALL} label="Any origin">Any origin</Select.Item>
				{#each Object.entries(TEMPLATE_ORIGIN_LABELS) as [value, label] (value)}
					<Select.Item {value} {label}>{label}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		{#if newCount > 0 || onlyNew}
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
		{#if onlyCallback}
			<Button
				variant="secondary"
				aria-label="Clear the need a callback filter"
				onclick={() => (onlyCallback = false)}
			>
				Need a callback
				<X class="size-3.5" />
			</Button>
		{/if}
		<Button
			variant="outline"
			size="icon"
			class="ml-auto"
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
		<RowSkeleton rows={6} avatar="size-7 rounded-md" trailing="h-5 w-20 rounded-full" />
	{:else if listError}
		<EmptyState
			icon={TriangleAlert}
			title="Checks not loaded"
			description={listError}
			class="rounded-none border-0 bg-transparent py-16"
		>
			<Button variant="outline" size="sm" onclick={() => void loadList()}>Retry</Button>
		</EmptyState>
	{:else if items.length === 0}
		<EmptyState
			icon={SearchX}
			title="No checks match"
			class="rounded-none border-0 bg-transparent py-16"
		/>
	{:else}
		<div class="divide-y">
			{#each items as template (template.id)}
				{@const custom = template.origin === TemplateOrigin.CUSTOM}
				{@const SetIcon = TEMPLATE_SET_ICONS[template.sets[0] ?? ''] ?? FileCode}
				<div class="flex items-start gap-3 px-4 py-3 hover:bg-muted/40">
					{#if custom && isAdmin}
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
							{#each template.cve_ids
								.filter((cve) => cve !== template.template_id)
								.slice(0, 1) as cve (cve)}
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
							size="icon-sm"
							class="text-muted-foreground hover:text-foreground"
							aria-label="{custom && isAdmin ? 'Edit' : 'View'} {template.name}"
							onclick={() => (viewing = template)}
						>
							<FileCode class="size-4" />
						</Button>
						<Switch
							checked={template.enabled}
							disabled={!isAdmin}
							onCheckedChange={(value) => toggle(template, value)}
							aria-label="Enable {template.name}"
						/>
						{#if custom && isAdmin}
							<Button
								variant="ghost"
								size="icon-sm"
								class="text-muted-foreground hover:text-destructive"
								aria-label="Delete {template.name}"
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
		<ResultsPagination {total} page={pageIndex} pageSize={PAGE_SIZE} noun="check" onPage={page} />
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
	title="Delete check"
	description={`Check ${removing?.name ?? ''} and its file are removed.`}
	confirmLabel="Delete"
	loadingLabel="Deleting"
	isDeleting={deleting}
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

<CallbackServerSheet
	bind:open={callbackOpen}
	settings={oast}
	failed={oastFailed}
	onRetry={loadOast}
	onSaved={(row) => (oast = row)}
/>
