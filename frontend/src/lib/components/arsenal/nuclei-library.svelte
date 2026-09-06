<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import Download from '@lucide/svelte/icons/download';
	import FilePlus from '@lucide/svelte/icons/file-plus';
	import FileCode from '@lucide/svelte/icons/file-code';
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
	import { ScrollArea } from '$lib/components/ui/scroll-area';
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
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';

	const PAGE_SIZE = 25;
	const ALL = 'all';

	let stats = $state<TemplateLibraryStats | null>(null);
	let statsLoading = $state(true);
	let items = $state<VulnTemplateRead[]>([]);
	let total = $state(0);
	let listLoading = $state(true);
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
	let fired = $state(false);
	let reqId = 0;

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
	let maxSet = $derived(Math.max(1, ...sets.map((spec) => spec.count)));

	function tileStyle(severity: string) {
		const fill = SEVERITY_FILL[severity] ?? SEVERITY_FILL.unknown;
		return `background:color-mix(in oklch, ${fill} 14%, transparent);color:color-mix(in oklch, ${fill} 85%, var(--foreground));box-shadow:inset 0 0 0 1px color-mix(in oklch, ${fill} 30%, transparent)`;
	}

	async function loadStats() {
		statsLoading = true;
		try {
			stats = await vulnTemplatesApi.stats();
		} catch {
			stats = null;
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
		} catch {
			if (my === reqId) {
				items = [];
				total = 0;
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
		const handle = setTimeout(() => untrack(loadList), SEARCH_DEBOUNCE_MS);
		return () => clearTimeout(handle);
	});

	$effect(() => {
		const q = search.trim() || null;
		const sev = severity === ALL ? [] : [severity];
		const org = origin === ALL ? [] : [origin];
		const chosen = set === ALL ? [] : [set];
		const onlyFired = fired;
		untrack(() => {
			filter = {
				...filter,
				q,
				severities: sev,
				origins: org,
				sets: chosen,
				fired: onlyFired,
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
			toast.error('Library sync could not be started');
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
					`${accepted} ${accepted === 1 ? 'check' : 'checks'} added to the library`,
					res.replaced
						? { description: `${res.replaced} replaced an existing template.` }
						: undefined
				);
			}
			for (const rejection of res.rejected) {
				toast.error(rejection.filename, { description: rejection.reason });
			}
			await Promise.all([loadStats(), loadList()]);
		} catch {
			toast.error('Upload failed');
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
			toast.error('Check could not be updated');
		}
	}

	async function remove() {
		const target = removing;
		if (!target) return;
		try {
			await vulnTemplatesApi.remove(target.id);
			toast.success(`Removed ${target.name}`);
			removing = null;
			await Promise.all([loadStats(), loadList()]);
		} catch {
			toast.error('Check could not be removed');
		}
	}

	function page(next: number) {
		filter = { ...filter, offset: Math.max(0, next) * PAGE_SIZE };
	}
</script>

<div class="space-y-6">
	<Card.Root>
		<Card.Header>
			<Card.Title>Check library</Card.Title>
			<Card.Description>
				Checks available to a vulnerability scan. Project templates come from the nuclei-templates
				repository. Templates you upload run alongside them.
			</Card.Description>
			<Card.Action class="flex items-center gap-2">
				<Button variant="outline" size="sm" class="gap-2" onclick={() => (creating = true)}>
					<FilePlus class="size-4" /> New check
				</Button>
				<input
					bind:this={fileInput}
					type="file"
					accept=".yaml,.yml"
					multiple
					class="hidden"
					onchange={upload}
				/>
				<LoadingButton
					variant="outline"
					size="sm"
					class="gap-2"
					loading={uploading}
					loadingLabel="Uploading…"
					onclick={() => fileInput?.click()}
				>
					<Upload class="size-4" /> Upload templates
				</LoadingButton>
				<LoadingButton
					size="sm"
					class="gap-2"
					loading={syncing}
					loadingLabel="Starting…"
					onclick={sync}
				>
					<Download class="size-4" /> Sync library
				</LoadingButton>
			</Card.Action>
		</Card.Header>
		<Card.Content class="space-y-4">
			{#if statsLoading}
				<Skeleton class="h-20 w-full" />
			{:else if !stats?.ready}
				<div
					class="flex items-start gap-3 rounded-md border border-warning/40 bg-warning/5 px-4 py-3"
				>
					<TriangleAlert class="mt-0.5 size-4 shrink-0 text-warning" />
					<div class="space-y-1">
						<p class="text-sm font-medium">The library is empty</p>
						<p class="text-sm text-muted-foreground">
							A vulnerability scan cannot run until the project templates are downloaded and
							indexed.
						</p>
					</div>
				</div>
			{:else}
				<div class="flex flex-wrap items-center gap-x-8 gap-y-3">
					<div class="flex flex-col">
						<span class="text-2xl leading-8 font-semibold tabular-nums">
							{stats.total.toLocaleString()}
						</span>
						<span class="text-xs text-muted-foreground">checks indexed</span>
					</div>
					<button
						type="button"
						class="flex flex-col text-left hover:opacity-80"
						onclick={() => (fired = !fired)}
						aria-pressed={fired}
					>
						<span class="text-sm font-medium tabular-nums">{stats.fired.toLocaleString()}</span>
						<span class="text-xs text-muted-foreground">with findings</span>
					</button>
					<div class="flex flex-col">
						<span class="text-sm font-medium tabular-nums">
							{stats.official.toLocaleString()}
						</span>
						<span class="text-xs text-muted-foreground">
							{TEMPLATE_ORIGIN_LABELS.official}
						</span>
					</div>
					<div class="flex flex-col">
						<span class="text-sm font-medium tabular-nums">{stats.custom.toLocaleString()}</span>
						<span class="text-xs text-muted-foreground">{TEMPLATE_ORIGIN_LABELS.custom}</span>
					</div>
					<div class="flex min-w-64 flex-1 flex-col gap-1.5">
						<SeverityBar
							counts={severityCounts}
							height="h-1.5"
							onPick={(s) => (severity = severity === s ? ALL : s)}
						/>
						<div class="flex flex-wrap gap-x-4 gap-y-1">
							{#each stats.by_severity as part (part.key)}
								<button
									type="button"
									class="flex items-center gap-1.5 text-xs hover:underline"
									onclick={() => (severity = severity === part.key ? ALL : part.key)}
								>
									<SeverityMark severity={part.key} showLabel={false} />
									<span class="text-muted-foreground">{part.label}</span>
									<span class="font-medium tabular-nums">{part.count.toLocaleString()}</span>
								</button>
							{/each}
						</div>
					</div>
					{#if stats.last_synced_at}
						<span class="ml-auto flex items-center gap-1.5 text-xs text-muted-foreground">
							<CircleCheck class="size-3.5 text-success" />
							Updated {relativeTime(stats.last_synced_at)}
						</span>
					{/if}
				</div>
			{/if}

			{#if sets.length}
				<div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
					{#each sets as spec (spec.key)}
						{@const Icon = TEMPLATE_SET_ICONS[spec.key]}
						{@const active = set === spec.key}
						<Hint text={spec.description}>
							{#snippet child(props)}
								<button
									{...props}
									type="button"
									class="flex flex-col gap-2 rounded-md border p-3 text-left transition-colors hover:bg-muted/40 {active
										? 'border-primary/50 bg-primary/5'
										: ''}"
									aria-pressed={active}
									onclick={() => (set = active ? ALL : spec.key)}
								>
									<span class="flex items-center gap-2">
										<span class="flex size-6 items-center justify-center rounded-md bg-muted">
											{#if Icon}<Icon class="size-3.5" />{/if}
										</span>
										<span class="min-w-0 truncate text-xs font-medium">{spec.label}</span>
									</span>
									<span class="text-lg leading-6 font-semibold tabular-nums">
										{spec.count.toLocaleString()}
									</span>
									<span class="flex h-1 w-full overflow-hidden rounded-full bg-muted">
										<span
											class="h-full rounded-full bg-[var(--chart-1)]"
											style="width:{(spec.count / maxSet) * 100}%"
										></span>
									</span>
								</button>
							{/snippet}
						</Hint>
					{/each}
				</div>
			{/if}

			<div class="rounded-md border">
				<div class="flex flex-wrap items-center gap-2 border-b p-3">
					<Input
						bind:value={search}
						placeholder="Search checks by name or identifier…"
						class="h-9 max-w-xs"
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
							{origin === ALL ? 'All sources' : TEMPLATE_ORIGIN_LABELS[origin]}
						</Select.Trigger>
						<Select.Content>
							<Select.Item value={ALL} label="All sources">All sources</Select.Item>
							{#each Object.entries(TEMPLATE_ORIGIN_LABELS) as [value, label] (value)}
								<Select.Item {value} {label}>{label}</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
					<ToggleGroup.Root
						type="single"
						value={fired ? 'fired' : ''}
						onValueChange={(v) => (fired = v === 'fired')}
						variant="outline"
						aria-label="Findings"
					>
						<ToggleGroup.Item value="fired" class="h-9 px-3 text-sm font-normal">
							Has findings
						</ToggleGroup.Item>
					</ToggleGroup.Root>
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
							<div class="px-4 py-3"><Skeleton class="h-9 w-full" /></div>
						{/each}
					</div>
				{:else if items.length === 0}
					<EmptyState
						icon={SearchX}
						title="No checks match"
						description="Widen the search or remove a filter."
						class="rounded-none border-0 bg-transparent py-12"
					/>
				{:else}
					<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-[32rem]">
						<div class="divide-y">
							{#each items as template (template.id)}
								{@const custom = template.origin === 'custom'}
								{@const SetIcon = TEMPLATE_SET_ICONS[template.sets[0] ?? ''] ?? FileCode}
								<div class="flex items-start gap-3 px-4 py-3">
									<span class="flex h-5 shrink-0 items-center">
										<span
											class="flex size-7 items-center justify-center rounded-md"
											style={tileStyle(template.severity)}
										>
											<SetIcon class="size-4" />
										</span>
									</span>
									<div class="flex min-w-0 flex-1 flex-col gap-1">
										<div class="flex flex-wrap items-center gap-2">
											<span class="text-sm leading-5 font-medium wrap-anywhere">
												{template.name}
											</span>
											{#if custom}
												<Badge variant="info" class="text-[10px] font-normal">Custom</Badge>
											{/if}
											{#if template.findings > 0}
												<Hint text="Findings this check has produced across every scan">
													{#snippet child(props)}
														<span {...props} class="flex h-5 items-center">
															<Badge
																variant="warning"
																class="px-1.5 text-[10px] font-normal tabular-nums"
															>
																{template.findings.toLocaleString()}
																{template.findings === 1 ? 'finding' : 'findings'}
															</Badge>
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
										<Hint text={custom ? 'View and edit the source' : 'View the source'}>
											{#snippet child(props)}
												<Button
													{...props}
													variant="ghost"
													size="icon"
													class="size-8 text-muted-foreground hover:text-foreground"
													aria-label="{custom ? 'Edit' : 'View'} {template.name}"
													onclick={() => (viewing = template)}
												>
													<FileCode class="size-4" />
												</Button>
											{/snippet}
										</Hint>
										<Hint
											text={template.enabled
												? 'Runs when a vulnerability plan selects it'
												: 'Excluded from every scan regardless of the plan'}
										>
											{#snippet child(props)}
												<span {...props} class="inline-flex">
													<Switch
														checked={template.enabled}
														onCheckedChange={(value) => toggle(template, value)}
														aria-label="Enable {template.name}"
													/>
												</span>
											{/snippet}
										</Hint>
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
					</ScrollArea>
				{/if}

				{#if total > PAGE_SIZE}
					<div class="flex items-center justify-between border-t px-4 py-2.5 text-xs">
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
			</div>

			<p class="text-xs text-muted-foreground">
				An uploaded template must be a nuclei document with an <code class="font-mono">id</code> and
				an <code class="font-mono">info.name</code>. Templates using the
				<code class="font-mono">code</code> protocol are rejected. That protocol executes commands on
				the scanner host.
			</p>
		</Card.Content>
	</Card.Root>
</div>

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
	title="Remove this check?"
	description="The check is removed from the library and deleted from disk. Scan engines that selected it run their remaining checks."
	confirmLabel="Remove"
	onConfirm={remove}
/>
