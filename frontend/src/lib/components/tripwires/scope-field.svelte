<script lang="ts">
	import { untrack } from 'svelte';
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
		onChange: (scope: TripwireScope, labels: string[]) => void;
		ids?: { kind: string; select: string };
	}

	let { projectSlug, scope, onChange, ids }: Props = $props();

	interface Item {
		id: string;
		label: string;
		color?: string;
	}

	let targets = $state<Item[]>([]);
	let organizations = $state<Organization[]>([]);
	let tags = $state<Tag[]>([]);
	let loaded = $state<string | null>(null);

	const KINDS = Object.values(ScopeKind);

	$effect(() => {
		const slug = projectSlug;
		if (!slug || loaded === slug) return;
		untrack(() => void load(slug));
	});

	async function load(slug: string) {
		loaded = slug;
		const [t, o, g] = await Promise.all([
			targetsApi.list({ project_slug: slug, size: 100 }).catch(() => null),
			organizationsApi.list({ project_slug: slug }).catch(() => []),
			tagsApi.list({ project_slug: slug }).catch(() => [])
		]);
		targets = (t?.items ?? []).map((x) => ({ id: x.id, label: x.target_value }));
		organizations = o;
		tags = g;
	}

	let selectedTargets = $derived(targets.filter((t) => scope.ids.includes(t.id)));
	let single = $derived(scope.ids[0] ?? '');
	let orgLabel = $derived(
		organizations.find((o) => o.id === single)?.name ?? 'Choose an organization'
	);
	let tagLabel = $derived(tags.find((t) => t.id === single)?.name ?? 'Choose a tag');

	function labelsOf(next: TripwireScope): string[] {
		if (next.kind === ScopeKind.Targets) {
			return next.ids.map((id) => targets.find((t) => t.id === id)?.label ?? id);
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
			allowCreate={false}
			placeholder="Search targets"
			emptyText="No targets in this project"
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
