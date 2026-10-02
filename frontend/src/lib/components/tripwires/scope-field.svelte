<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteMap } from 'svelte/reactivity';
	import * as Select from '$lib/components/ui/select';
	import MultiSelectCombobox from '$lib/components/multi-select-combobox.svelte';
	import { organizationsApi, type Organization } from '$lib/api/organizations';
	import { tagsApi, type Tag } from '$lib/api/tags';
	import { targetsApi } from '$lib/api/targets';
	import { SCOPE_LABELS, ScopeKind } from '$lib/config/tripwires';
	import type { TripwireScope } from '$lib/types/tripwire';

	interface Props {
		projectSlug: string;
		scope: TripwireScope;
		labels?: string[];
		onChange: (scope: TripwireScope, labels: string[]) => void;
		ids?: { kind: string; select: string };
	}

	let { projectSlug, scope, labels = [], onChange, ids }: Props = $props();

	interface Item {
		id: string;
		label: string;
		color?: string;
	}

	let targets = $state<Item[]>([]);
	let organizations = $state<Organization[]>([]);
	let tags = $state<Tag[]>([]);
	let loaded = $state<string | null>(null);
	let ready = $state(false);

	const KINDS = Object.values(ScopeKind);
	const SEARCH_ROWS = 50;
	const SEARCH_DEBOUNCE_MS = 200;
	const names = new SvelteMap<string, string>(
		untrack(() =>
			labels.length === scope.ids.length
				? scope.ids.map((id, i): [string, string] => [id, labels[i]])
				: []
		)
	);
	const asked: string[] = [];
	let seq = 0;
	let timer: ReturnType<typeof setTimeout> | undefined;

	$effect(() => {
		const slug = projectSlug;
		if (!slug || loaded === slug) return;
		untrack(() => void load(slug));
	});

	$effect(() => {
		if (!ready || scope.kind !== ScopeKind.Targets) return;
		const missing = scope.ids.filter((id) => !untrack(() => names.has(id)) && !asked.includes(id));
		for (const id of missing) {
			asked.push(id);
			targetsApi
				.get(id)
				.then((t) => names.set(t.id, t.target_value))
				.catch(() => {});
		}
	});

	async function load(slug: string) {
		loaded = slug;
		const [o, g] = await Promise.all([
			organizationsApi.list({ project_slug: slug }).catch(() => []),
			tagsApi.list({ project_slug: slug }).catch(() => []),
			runSearch('')
		]);
		organizations = o;
		tags = g;
		ready = true;
	}

	function searchTargets(q: string) {
		clearTimeout(timer);
		timer = setTimeout(() => void runSearch(q), q ? SEARCH_DEBOUNCE_MS : 0);
	}

	async function runSearch(q: string) {
		const mySeq = ++seq;
		const page = await targetsApi
			.list({
				project_slug: projectSlug,
				search: q,
				sort_by: 'name',
				sort_dir: 'asc',
				size: SEARCH_ROWS
			})
			.catch(() => null);
		if (mySeq !== seq) return;
		targets = (page?.items ?? []).map((x) => ({ id: x.id, label: x.target_value }));
		for (const x of targets) names.set(x.id, x.label);
	}

	let selectedTargets = $derived(scope.ids.map((id) => ({ id, label: names.get(id) ?? '…' })));
	let single = $derived(scope.ids[0] ?? '');
	let orgLabel = $derived(
		organizations.find((o) => o.id === single)?.name ?? 'Choose an organization'
	);
	let tagLabel = $derived(tags.find((t) => t.id === single)?.name ?? 'Choose a tag');

	function labelsOf(next: TripwireScope): string[] {
		if (next.kind === ScopeKind.Targets) {
			return next.ids.flatMap((id) => names.get(id) ?? []);
		}
		if (next.kind === ScopeKind.Organization) {
			return next.ids.map((id) => organizations.find((o) => o.id === id)?.name ?? id);
		}
		if (next.kind === ScopeKind.Tag) {
			return next.ids.map((id) => tags.find((t) => t.id === id)?.name ?? id);
		}
		return [];
	}

	function change(next: TripwireScope) {
		onChange(next, labelsOf(next));
	}

	function setKind(kind: string) {
		if (!kind) return;
		change({ kind, ids: kind === scope.kind ? scope.ids : [] });
	}
</script>

<div class="flex flex-col gap-2">
	<Select.Root type="single" value={scope.kind} onValueChange={setKind}>
		<Select.Trigger id={ids?.kind} class="w-full"
			>{SCOPE_LABELS[scope.kind as ScopeKind]}</Select.Trigger
		>
		<Select.Content>
			{#each KINDS as kind (kind)}
				<Select.Item value={kind} label={SCOPE_LABELS[kind]}>{SCOPE_LABELS[kind]}</Select.Item>
			{/each}
		</Select.Content>
	</Select.Root>

	{#if scope.kind === ScopeKind.Targets}
		<MultiSelectCombobox
			items={targets}
			selected={selectedTargets}
			onSelect={(item) =>
				change({
					...scope,
					ids: scope.ids.includes(item.id) ? scope.ids : [...scope.ids, item.id]
				})}
			onRemove={(item) => change({ ...scope, ids: scope.ids.filter((id) => id !== item.id) })}
			onSearch={searchTargets}
			allowCreate={false}
			placeholder="Search targets"
			emptyText="No targets"
		/>
	{:else if scope.kind === ScopeKind.Organization}
		<Select.Root
			type="single"
			value={single}
			onValueChange={(v) => v && change({ ...scope, ids: [v] })}
		>
			<Select.Trigger id={ids?.select} class="w-full">{orgLabel}</Select.Trigger>
			<Select.Content>
				{#each organizations as org (org.id)}
					<Select.Item value={org.id} label={org.name}>{org.name}</Select.Item>
				{/each}
				{#if organizations.length === 0}
					<div class="px-2 py-1.5 text-xs text-muted-foreground">No organizations</div>
				{/if}
			</Select.Content>
		</Select.Root>
	{:else if scope.kind === ScopeKind.Tag}
		<Select.Root
			type="single"
			value={single}
			onValueChange={(v) => v && change({ ...scope, ids: [v] })}
		>
			<Select.Trigger id={ids?.select} class="w-full">{tagLabel}</Select.Trigger>
			<Select.Content>
				{#each tags as tag (tag.id)}
					<Select.Item value={tag.id} label={tag.name}>{tag.name}</Select.Item>
				{/each}
				{#if tags.length === 0}
					<div class="px-2 py-1.5 text-xs text-muted-foreground">No tags</div>
				{/if}
			</Select.Content>
		</Select.Root>
	{/if}
</div>
