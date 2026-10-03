<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import ResultCell from './result-cell.svelte';
	import Search from '@lucide/svelte/icons/search';
	import Copy from '@lucide/svelte/icons/copy';
	import X from '@lucide/svelte/icons/x';
	import Plus from '@lucide/svelte/icons/plus';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { ROUTES } from '$lib/config/routes';
	import { ADD_TARGETS_BATCH, SELECT_FILTER_AT, SELECT_ROW_PAGE } from '$lib/config/toolbox';
	import type { Cell, ResultBlock } from '$lib/types/toolbox';

	interface Props {
		block: ResultBlock;
		organization?: string | null;
		onLookup?: (value: string, tool: string | null) => void;
		onNavigate?: () => void;
	}

	let { block, organization = null, onLookup, onNavigate }: Props = $props();

	interface Entry {
		cells: Cell[];
		key: string | null;
		text: string;
	}

	const picked = new SvelteSet<string>();
	const added = new SvelteMap<string, { id: string | null; existed: boolean }>();
	let query = $state('');
	let limit = $state(SELECT_ROW_PAGE);
	let group = $state(true);
	let adding = $state(false);

	const project = $derived(projectsStore.activeProject);
	const entries = $derived<Entry[]>(
		block.rows.map((cells, i) => ({
			cells,
			key: block.keys[i] ?? null,
			text: cells
				.map((c) => c.value)
				.join(' ')
				.toLowerCase()
		}))
	);
	const needle = $derived(query.trim().toLowerCase());
	const filtered = $derived(needle ? entries.filter((e) => e.text.includes(needle)) : entries);
	const visible = $derived(filtered.slice(0, limit));
	const remaining = $derived(filtered.length - visible.length);
	const open = (e: Entry) => e.key !== null && !added.has(e.key);
	const pickable = $derived(filtered.filter(open).map((e) => e.key as string));
	const allPicked = $derived(pickable.length > 0 && pickable.every((k) => picked.has(k)));
	const somePicked = $derived(!allPicked && pickable.some((k) => picked.has(k)));
	const noun = (n: number) => (n === 1 ? 'target' : 'targets');

	$effect(() => {
		void needle;
		limit = SELECT_ROW_PAGE;
	});

	$effect(() => {
		void block;
		untrack(() => {
			picked.clear();
			added.clear();
			query = '';
		});
	});

	function tracked(done: { id: string | null; existed: boolean }): Cell {
		return {
			value: 'Target',
			tone: 'success',
			note: done.existed ? null : 'added',
			href: done.id ? ROUTES.target(done.id) : null,
			mono: false,
			identity: null,
			lookup: null
		};
	}

	function toggle(key: string, on: boolean) {
		if (on) picked.add(key);
		else picked.delete(key);
	}

	function toggleAll() {
		if (allPicked) for (const k of pickable) picked.delete(k);
		else for (const k of pickable) picked.add(k);
	}

	async function copy() {
		const ok = await writeClipboard([...picked].join('\n'));
		if (ok) toast.success(`${picked.size} copied`);
		else toast.error('Not copied. The browser blocked clipboard access.');
	}

	async function add() {
		if (!project) {
			toast.error('No project selected. Select a project, then add targets.');
			return;
		}
		const values = [...picked];
		const organizations = group && organization ? [organization] : [];
		let imported = 0;
		let existing = 0;
		const failures: string[] = [];
		let stopped: string | null = null;
		adding = true;
		for (let i = 0; i < values.length; i += ADD_TARGETS_BATCH) {
			try {
				const response = await targetsApi.bulkCreate({
					project_slug: project.slug,
					targets: values.slice(i, i + ADD_TARGETS_BATCH),
					organization_names: organizations
				});
				imported += response.imported;
				existing += response.skipped_duplicates;
				for (const result of response.results) {
					if (result.success || result.duplicate) {
						added.set(result.target_value, {
							id: result.target_id,
							existed: result.duplicate
						});
					} else failures.push(`${result.target_value}: ${result.error ?? 'not added'}`);
				}
			} catch (e) {
				stopped = e instanceof Error ? e.message : 'The API did not respond.';
				break;
			}
		}
		adding = false;
		for (const key of added.keys()) picked.delete(key);
		if (imported) void targetsStore.refresh();
		if (stopped) {
			toast.error(
				imported ? `${imported} of ${values.length} targets added` : 'Targets not added',
				{ description: stopped }
			);
			return;
		}
		if (imported) {
			toast.success(`${imported} ${noun(imported)} added`, {
				description: existing ? `${existing} already in this project` : undefined
			});
		} else if (existing) {
			toast.info(`${existing} already in this project`);
		}
		if (failures.length) {
			toast.warning(`${failures.length} not added`, {
				description: failures.slice(0, 3).join('\n')
			});
		}
	}
</script>

<div class="space-y-2">
	{#if block.rows.length > SELECT_FILTER_AT}
		<div class="flex items-center gap-2">
			<div class="relative max-w-xs flex-1">
				<Search
					class="pointer-events-none absolute top-1/2 left-2 size-3.5 -translate-y-1/2 text-muted-foreground"
				/>
				<Input
					bind:value={query}
					placeholder="Filter"
					aria-label="Filter rows"
					class="h-7 pl-7 text-xs"
				/>
			</div>
			{#if needle}
				<span class="font-mono text-2xs text-muted-foreground">
					{filtered.length} of {entries.length}
				</span>
			{/if}
		</div>
	{/if}

	<ScrollArea orientation="horizontal" class="w-full">
		<table class="w-full min-w-full text-left">
			<thead>
				<tr class="border-b border-border bg-muted/20">
					<th class="w-6 py-2 pl-2 align-middle">
						<Checkbox
							checked={allPicked}
							indeterminate={somePicked}
							disabled={pickable.length === 0}
							onCheckedChange={toggleAll}
							aria-label="Select all rows"
						/>
					</th>
					{#each block.columns as column (column)}
						<th
							class="px-2 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
						>
							{column}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each visible as entry, i (entry.key ?? `row:${i}`)}
					{@const done = entry.key !== null ? added.get(entry.key) : undefined}
					<tr
						class="border-b border-border/60 last:border-0 {entry.key && picked.has(entry.key)
							? 'bg-muted/40'
							: ''}"
					>
						<td class="py-1 pl-2 align-top">
							<span class="flex h-5 items-center">
								{#if done}
									<CircleCheck
										class="size-4 {done.existed ? 'text-muted-foreground' : 'text-success'}"
										aria-label={done.existed ? 'Already a target' : 'Added as a target'}
									/>
								{:else if entry.key !== null}
									<Checkbox
										checked={picked.has(entry.key)}
										onCheckedChange={(on) => toggle(entry.key as string, on === true)}
										aria-label="Select {entry.key}"
									/>
								{/if}
							</span>
						</td>
						{#each entry.cells as cell, j (j)}
							<td class="px-2 py-1 align-top">
								<ResultCell
									cell={done && j === entry.cells.length - 1 ? tracked(done) : cell}
									{onLookup}
									{onNavigate}
								/>
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</ScrollArea>

	{#if filtered.length === 0}
		<p class="text-sm text-muted-foreground">No rows match the filter.</p>
	{:else if remaining > 0}
		<div class="flex items-center gap-3 border-t border-border/60 px-2 pt-1.5 text-xs">
			<button
				type="button"
				onclick={() => (limit += SELECT_ROW_PAGE)}
				class="text-muted-foreground hover:text-foreground"
			>
				Show {Math.min(SELECT_ROW_PAGE, remaining)} more
			</button>
			<button
				type="button"
				onclick={() => (limit = filtered.length)}
				class="text-muted-foreground hover:text-foreground"
			>
				Show all {filtered.length}
			</button>
		</div>
	{/if}

	{#if picked.size > 0}
		<div class="sticky bottom-2 z-10 flex justify-center pt-1">
			<div
				class="flex flex-wrap items-center gap-0.5 gap-y-1 rounded-lg border border-border bg-popover p-1.5 text-popover-foreground shadow-md"
				role="region"
				aria-label="Selection actions"
			>
				<span class="px-2.5 py-1 text-xs font-medium text-muted-foreground tabular-nums">
					{picked.size} selected
				</span>
				<Separator orientation="vertical" class="mx-0.5 h-4 self-center" />
				<Button variant="ghost" size="sm" onclick={copy}>
					<Copy class="size-3.5" />
					Copy
				</Button>
				{#if organization}
					<label class="flex cursor-pointer items-center gap-1.5 px-2 text-xs">
						<Checkbox bind:checked={group} aria-label="Group under {organization}" />
						Group under <span class="max-w-40 truncate font-medium">{organization}</span>
					</label>
				{/if}
				{#if project}
					<LoadingButton size="sm" loading={adding} loadingLabel="Adding" onclick={add}>
						<Plus class="size-3.5" />
						Add {picked.size}
						{noun(picked.size)}
					</LoadingButton>
				{:else}
					<Hint text="No project selected">
						{#snippet child(props)}
							<span {...props} class="inline-flex">
								<Button size="sm" disabled>
									<Plus class="size-3.5" />
									Add {picked.size}
									{noun(picked.size)}
								</Button>
							</span>
						{/snippet}
					</Hint>
				{/if}
				<Separator orientation="vertical" class="mx-0.5 h-4 self-center" />
				<Button
					variant="ghost"
					size="icon-sm"
					class="text-muted-foreground"
					aria-label="Clear selection"
					onclick={() => picked.clear()}
				>
					<X class="size-3.5" />
				</Button>
			</div>
		</div>
	{/if}
</div>
