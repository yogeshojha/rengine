<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Cell from '$lib/components/cell.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Textarea } from '$lib/components/ui/textarea';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Badge } from '$lib/components/ui/badge';
	import * as Dialog from '$lib/components/ui/dialog';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import { plural } from '$lib/utilities/strings';
	import type { TargetSeed, TargetSeedRejection } from '$lib/types/target';

	interface Props {
		targetId: string;
		class?: string;
	}

	let { targetId, class: className = '' }: Props = $props();

	const VISIBLE = 6;

	let seeds = $state<TargetSeed[]>([]);
	let loading = $state(true);
	let failed = $state(false);
	let adding = $state(false);
	let removing = $state(false);
	let removeOpen = $state(false);
	let pendingRemove = $state<TargetSeed | null>(null);
	let draft = $state('');
	let rejected = $state<TargetSeedRejection[]>([]);
	let loadedFor = $state<string | null>(null);
	let open = $state(false);

	let lines = $derived(
		draft
			.split(/[\s,]+/)
			.map((line) => line.trim())
			.filter(Boolean)
	);

	const guard = new DiscardGuard(
		() => draft.trim() !== '',
		() => {
			open = false;
			draft = '';
			rejected = [];
		}
	);

	$effect(() => {
		if (loadedFor === targetId) return;
		loadedFor = targetId;
		untrack(() => load());
	});

	async function load() {
		loading = true;
		try {
			seeds = await targetsApi.listSeeds(targetId);
			failed = false;
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	}

	async function add() {
		if (!lines.length) return;
		adding = true;
		try {
			const result = await targetsApi.writeSeeds(targetId, lines);
			rejected = result.rejected;
			draft = '';
			await load();
			if (result.added > 0) toast.success(`${plural(result.added, 'seed asset')} stored`);
			if (!result.rejected.length) open = false;
		} catch {
			toast.error('Seed assets not stored');
		} finally {
			adding = false;
		}
	}

	async function remove() {
		const seed = pendingRemove;
		if (!seed) return;
		removing = true;
		try {
			await targetsApi.deleteSeed(targetId, seed.id);
			seeds = seeds.filter((s) => s.id !== seed.id);
			removeOpen = false;
		} catch {
			toast.error('Seed asset not removed');
		} finally {
			removing = false;
		}
	}
</script>

<Cell
	skeleton="list"
	id="seeds"
	title="Seed assets"
	loading={loading && !seeds.length}
	class={className}
>
	{#snippet tools()}
		<Button variant="outline" size="sm" class="h-7 px-2 text-xs" onclick={() => (open = true)}>
			<Plus class="size-3.5" />
			Add
		</Button>
	{/snippet}
	{#if seeds.length}
		<ScrollArea class={seeds.length > VISIBLE ? 'h-48' : ''}>
			<ul class="flex flex-col">
				{#each seeds as seed (seed.id)}
					<li class="flex items-center gap-2 border-t py-0.5 first:border-t-0">
						<span class="min-w-0 flex-1 font-mono text-xs break-all">{seed.value}</span>
						{#if seed.kind !== 'host'}
							<Badge variant="outline" class="font-normal">{seed.kind}</Badge>
						{/if}
						<Button
							variant="ghost"
							size="icon"
							class="size-7 shrink-0"
							onclick={() => {
								pendingRemove = seed;
								removeOpen = true;
							}}
							aria-label="Remove {seed.value}"
						>
							<X class="size-3.5" />
						</Button>
					</li>
				{/each}
			</ul>
		</ScrollArea>
	{:else if loading}
		<Skeleton class="h-4 w-2/3" />
	{:else if failed}
		<div class="flex flex-wrap items-center gap-3">
			<span class="text-sm text-muted-foreground">Seed assets not loaded</span>
			<Button variant="outline" size="sm" onclick={() => load()}>Retry</Button>
		</div>
	{:else}
		<span class="text-sm text-muted-foreground">No seed assets</span>
	{/if}
	{#snippet footer()}
		<span>{seeds.length.toLocaleString()} stored</span>
	{/snippet}
</Cell>

<Dialog.Root bind:open={() => open, (next) => (next ? (open = true) : !adding && guard.close())}>
	<Dialog.Content class="sm:max-w-lg">
		<Dialog.Header>
			<Dialog.Title>Add seed assets</Dialog.Title>
			<Dialog.Description>One host name, address or URL per line.</Dialog.Description>
		</Dialog.Header>
		<div class="flex flex-col gap-3">
			<Textarea
				rows={6}
				placeholder="www.example.com"
				bind:value={draft}
				aria-label="Seed assets"
				class="font-mono text-xs"
			/>
			{#if rejected.length > 0}
				<div class="flex flex-col gap-1">
					{#each rejected as item, i (item.value + i)}
						<div class="flex items-baseline gap-2 text-xs">
							<span class="font-mono break-all text-muted-foreground">{item.value}</span>
							<span class="text-destructive">{item.reason}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
		<Dialog.Footer>
			<Button variant="outline" disabled={adding} onclick={() => guard.close()}>Cancel</Button>
			<LoadingButton loading={adding} loadingLabel="Adding" disabled={!lines.length} onclick={add}>
				<Plus />
				Add
			</LoadingButton>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>

<ConfirmDialog
	open={removeOpen}
	title="Remove seed asset"
	description="Seed asset {pendingRemove?.value ?? ''} is removed."
	confirmLabel="Remove"
	loading={removing}
	loadingLabel="Removing"
	destructive
	onOpenChange={(next) => (removeOpen = next)}
	onConfirm={remove}
/>
