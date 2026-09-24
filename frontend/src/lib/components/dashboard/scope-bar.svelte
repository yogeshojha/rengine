<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteMap } from 'svelte/reactivity';
	import Crosshair from '@lucide/svelte/icons/crosshair';
	import Building2 from '@lucide/svelte/icons/building-2';
	import TagIcon from '@lucide/svelte/icons/tag';
	import { Button } from '$lib/components/ui/button';
	import ScopePicker, { type PickerItem } from './scope-picker.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { organizationsApi } from '$lib/api/organizations';
	import { tagsApi } from '$lib/api/tags';
	import { isScoped, type TargetScope } from '$lib/utilities/surface-scope';

	interface Props {
		projectSlug: string;
		scope: TargetScope;
		known: { id: string; value: string }[];
		onChange: (scope: TargetScope) => void;
	}

	let { projectSlug, scope, known, onChange }: Props = $props();

	const SEARCH_ROWS = 50;
	const SEARCH_DEBOUNCE_MS = 200;

	const names = new SvelteMap<string, string>();
	let targetItems = $state<PickerItem[]>([]);
	let targetsLoading = $state(false);
	let organizations = $state<PickerItem[]>([]);
	let tags = $state<PickerItem[]>([]);
	let seq = 0;
	let timer: ReturnType<typeof setTimeout> | undefined;

	$effect(() => {
		for (const t of known) names.set(t.id, t.value);
	});

	$effect(() => {
		const slug = projectSlug;
		untrack(() => void loadLabels(slug));
	});

	$effect(() => {
		const missing = (scope.targetIds ?? []).filter((id) => !untrack(() => names.has(id)));
		for (const id of missing) {
			targetsApi
				.get(id)
				.then((t) => names.set(t.id, t.target_value))
				.catch(() => {});
		}
	});

	async function loadLabels(slug: string) {
		const [orgs, tagRows] = await Promise.all([
			organizationsApi.list({ project_slug: slug }).catch(() => []),
			tagsApi.list({ project_slug: slug }).catch(() => [])
		]);
		organizations = orgs.map((o) => ({ id: o.id, label: o.name }));
		tags = tagRows.map((t) => ({ id: t.id, label: t.name, color: t.color }));
	}

	function searchTargets(q: string) {
		clearTimeout(timer);
		timer = setTimeout(() => void runSearch(q), q ? SEARCH_DEBOUNCE_MS : 0);
	}

	async function runSearch(q: string) {
		const mySeq = ++seq;
		targetsLoading = true;
		try {
			const page = await targetsApi.list({
				project_slug: projectSlug,
				search: q,
				sort_by: 'name',
				sort_dir: 'asc',
				size: SEARCH_ROWS
			});
			if (mySeq !== seq) return;
			for (const t of page.items) names.set(t.id, t.target_value);
			const selected = (scope.targetIds ?? []).map((id) => ({
				id,
				label: names.get(id) ?? id
			}));
			const rest = page.items
				.filter((t) => !scope.targetIds?.includes(t.id))
				.map((t) => ({ id: t.id, label: t.target_value }));
			targetItems = q ? rest : [...selected, ...rest];
		} catch {
			if (mySeq === seq) targetItems = [];
		} finally {
			if (mySeq === seq) targetsLoading = false;
		}
	}

	const labelIn = (items: PickerItem[]) => (id: string) =>
		items.find((i) => i.id === id)?.label ?? '';
	const one = (id?: string) => (id ? [id] : []);
</script>

<div class="flex flex-wrap items-center gap-2" role="group" aria-label="Scope">
	<ScopePicker
		label="Target"
		icon={Crosshair}
		items={targetItems}
		selected={scope.targetIds ?? []}
		labelOf={(id) => names.get(id) ?? '…'}
		multiple
		loading={targetsLoading}
		placeholder="Search targets"
		onSearch={searchTargets}
		onChange={(ids) => onChange({ ...scope, targetIds: ids.length ? ids : undefined })}
	/>
	{#if organizations.length || scope.organizationId}
		<ScopePicker
			label="Organization"
			icon={Building2}
			items={organizations}
			selected={one(scope.organizationId)}
			labelOf={labelIn(organizations)}
			placeholder="Search organizations"
			onChange={(ids) => onChange({ ...scope, organizationId: ids[0] })}
		/>
	{/if}
	{#if tags.length || scope.tagId}
		<ScopePicker
			label="Tag"
			icon={TagIcon}
			items={tags}
			selected={one(scope.tagId)}
			labelOf={labelIn(tags)}
			placeholder="Search tags"
			onChange={(ids) => onChange({ ...scope, tagId: ids[0] })}
		/>
	{/if}
	{#if isScoped(scope)}
		<Button
			variant="ghost"
			size="sm"
			class="h-8 text-muted-foreground"
			onclick={() => onChange({})}
		>
			Clear
		</Button>
	{/if}
</div>
