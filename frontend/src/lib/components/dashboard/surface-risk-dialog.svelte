<script lang="ts">
	import { untrack } from 'svelte';
	import * as Dialog from '$lib/components/ui/dialog';
	import * as Select from '$lib/components/ui/select';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Input } from '$lib/components/ui/input';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import SurfaceRiskRows from './surface-risk-rows.svelte';
	import { dashboardApi } from '$lib/api/dashboard';
	import { organizationsApi, type Organization } from '$lib/api/organizations';
	import { tagsApi, type Tag } from '$lib/api/tags';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { SEVERITY_FILL, SEVERITY_ORDER, severityLabel } from '$lib/config/vulnerabilities';
	import type { DashboardSurfaceRisk, SurfaceRiskTarget } from '$lib/types/dashboard';

	let { open = $bindable(false) }: { open: boolean } = $props();

	const SORTS = [
		{ value: 'findings', label: 'Sort by findings' },
		{ value: 'actionable', label: 'Sort by actionable' },
		{ value: 'live', label: 'Sort by live web assets' },
		{ value: 'name', label: 'Sort by name' }
	] as const;
	type SortKey = (typeof SORTS)[number]['value'];

	let project = $derived(projectsStore.activeProject);
	let data = $state<DashboardSurfaceRisk | null>(null);
	let loading = $state(false);
	let failed = $state(false);
	let organizations = $state<Organization[]>([]);
	let tags = $state<Tag[]>([]);
	let query = $state('');
	let organizationId = $state('');
	let tagId = $state('');
	let severities = $state<string[]>([...SEVERITY_ORDER]);
	let sort = $state<SortKey>('findings');
	let seq = 0;

	async function load() {
		const pid = project?.id;
		if (!pid) return;
		const mySeq = ++seq;
		loading = true;
		try {
			const out = await dashboardApi.surfaceRisk(pid, {
				organizationId: organizationId || null,
				tagId: tagId || null
			});
			if (mySeq !== seq) return;
			data = out;
			failed = false;
		} catch {
			if (mySeq !== seq) return;
			failed = true;
		} finally {
			if (mySeq === seq) loading = false;
		}
	}

	async function loadLabels() {
		const slug = project?.slug;
		if (!slug) return;
		const [orgs, tagRows] = await Promise.all([
			organizationsApi.list({ project_slug: slug }).catch(() => []),
			tagsApi.list({ project_slug: slug }).catch(() => [])
		]);
		organizations = orgs;
		tags = tagRows;
	}

	$effect(() => {
		if (!open) return;
		untrack(() => {
			void load();
			void loadLabels();
		});
	});

	const shown = (r: SurfaceRiskTarget) =>
		severities.reduce((n, s) => n + (r.by_severity[s] ?? 0), 0);
	const match = (value: string) =>
		!query || value.toLowerCase().includes(query.trim().toLowerCase());
	let rows = $derived.by(() => {
		const list = (data?.rows ?? []).filter((r) => match(r.target_value));
		const cmp: Record<SortKey, (a: SurfaceRiskTarget, b: SurfaceRiskTarget) => number> = {
			findings: (a, b) => shown(b) - shown(a) || b.live - a.live,
			actionable: (a, b) => b.actionable - a.actionable || shown(b) - shown(a),
			live: (a, b) => b.live - a.live || shown(b) - shown(a),
			name: (a, b) => a.target_value.localeCompare(b.target_value)
		};
		return [...list].sort(cmp[sort]);
	});
	let present = $derived(
		SEVERITY_ORDER.filter((s) => (data?.rows ?? []).some((r) => r.by_severity[s]))
	);
	let organizationLabel = $derived(
		organizations.find((o) => o.id === organizationId)?.name ?? 'All organizations'
	);
	let tagLabel = $derived(tags.find((t) => t.id === tagId)?.name ?? 'All tags');
	let sortLabel = $derived(SORTS.find((s) => s.value === sort)?.label ?? '');

	function setOrganization(value: string) {
		organizationId = value === 'all' ? '' : value;
		void load();
	}
	function setTag(value: string) {
		tagId = value === 'all' ? '' : value;
		void load();
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content
		class="flex max-h-[min(88vh,56rem)] flex-col gap-0 p-0 sm:max-w-[68rem]"
		showCloseButton={true}
	>
		<Dialog.Header class="border-b px-5 pt-4 pb-3 text-left">
			<Dialog.Title>Surface against risk</Dialog.Title>
			<Dialog.Description
				>Live web assets against open findings, every target in the project</Dialog.Description
			>
		</Dialog.Header>

		<div class="flex flex-wrap items-center gap-2 border-b px-5 py-3">
			<Input
				id="surface-risk-query"
				type="search"
				placeholder="Filter targets"
				aria-label="Filter targets"
				class="h-8 w-44 text-xs"
				bind:value={query}
			/>
			<Select.Root
				type="single"
				value={organizationId || 'all'}
				onValueChange={setOrganization}
				disabled={!organizations.length}
			>
				<Select.Trigger class="h-8 w-44 text-xs" aria-label="Organization">
					{organizations.length ? organizationLabel : 'No organizations'}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value="all" label="All organizations">All organizations</Select.Item>
					{#each organizations as o (o.id)}
						<Select.Item value={o.id} label={o.name}>{o.name}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
			<Select.Root
				type="single"
				value={tagId || 'all'}
				onValueChange={setTag}
				disabled={!tags.length}
			>
				<Select.Trigger class="h-8 w-40 text-xs" aria-label="Tag">
					{tags.length ? tagLabel : 'No tags'}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value="all" label="All tags">All tags</Select.Item>
					{#each tags as t (t.id)}
						<Select.Item value={t.id} label={t.name}>
							<span class="size-2 rounded-full" style="background:{t.color}"></span>
							{t.name}
						</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
			<span class="mx-1 hidden h-5 w-px bg-border sm:block"></span>
			<ToggleGroup.Root
				type="multiple"
				variant="outline"
				size="sm"
				bind:value={severities}
				aria-label="Severity"
			>
				{#each present as s (s)}
					<ToggleGroup.Item value={s} class="gap-1.5 px-2.5 text-xs" aria-label={severityLabel(s)}>
						<span class="size-2 rounded-full" style="background:{SEVERITY_FILL[s]}"></span>
						{severityLabel(s)}
					</ToggleGroup.Item>
				{/each}
			</ToggleGroup.Root>
			<span class="mx-1 hidden h-5 w-px bg-border sm:block"></span>
			<Select.Root type="single" bind:value={sort}>
				<Select.Trigger class="h-8 w-48 text-xs" aria-label="Sort">{sortLabel}</Select.Trigger>
				<Select.Content>
					{#each SORTS as s (s.value)}
						<Select.Item value={s.value} label={s.label}>{s.label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>

		{#if data}
			<div class="grid grid-cols-3 gap-2 px-5 pt-3">
				<div class="flex min-w-0 flex-col rounded-md bg-muted/60 px-2.5 py-1.5">
					<span class="text-lg leading-tight font-semibold tracking-tight tabular-nums">
						{data.live.toLocaleString()}
					</span>
					<span class="truncate text-2xs text-muted-foreground">live web assets</span>
				</div>
				<div class="flex min-w-0 flex-col rounded-md bg-muted/60 px-2.5 py-1.5">
					<span class="text-lg leading-tight font-semibold tracking-tight tabular-nums">
						{data.findings.toLocaleString()}
					</span>
					<span class="truncate text-2xs text-muted-foreground">open findings</span>
				</div>
				<div class="flex min-w-0 flex-col rounded-md bg-muted/60 px-2.5 py-1.5">
					<span
						class="text-lg leading-tight font-semibold tracking-tight tabular-nums {data.actionable
							? 'text-[var(--sev-critical-ink)]'
							: ''}"
					>
						{data.actionable.toLocaleString()}
					</span>
					<span class="truncate text-2xs text-muted-foreground">
						actionable · {data.act.toLocaleString()} act now
					</span>
				</div>
			</div>
		{/if}

		<ScrollArea class="min-h-0 flex-1">
			<div class="flex flex-col gap-3 px-5 py-3">
				{#if loading && !data}
					<div class="flex flex-col gap-2">
						{#each Array(6) as _, i (i)}
							<Skeleton class="h-8 w-full" />
						{/each}
					</div>
				{:else if failed && !data}
					<p class="py-8 text-center text-sm text-muted-foreground">
						Surface against risk did not load.
					</p>
				{:else if rows.length}
					{#key data}
						<SurfaceRiskRows {rows} {severities} wide />
					{/key}
				{:else}
					<p class="py-8 text-center text-sm text-muted-foreground">No scanned target matches.</p>
				{/if}
			</div>
		</ScrollArea>

		<div
			class="flex flex-wrap items-center gap-x-3 gap-y-1 border-t px-5 py-2 text-2xs text-muted-foreground"
		>
			<span class="flex items-center gap-1.5">
				<span class="size-2.5 rounded-[2px]" style="background:var(--series)"></span>
				Live web assets
			</span>
			{#each present as s (s)}
				<span class="flex items-center gap-1.5">
					<span class="size-2.5 rounded-[2px]" style="background:{SEVERITY_FILL[s]}"></span>
					{severityLabel(s)}
				</span>
			{/each}
		</div>
	</Dialog.Content>
</Dialog.Root>
