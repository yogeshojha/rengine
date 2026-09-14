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
	import { targetsApi } from '$lib/api/targets';
	import type { TargetSeed, TargetSeedRejection } from '$lib/types/target';

	interface Props {
		targetId: string;
		class?: string;
	}

	let { targetId, class: className = '' }: Props = $props();

	const VISIBLE = 6;

	let seeds = $state<TargetSeed[]>([]);
	let loading = $state(true);
	let adding = $state(false);
	let removing = $state<string | null>(null);
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

	$effect(() => {
		if (loadedFor === targetId) return;
		loadedFor = targetId;
		untrack(() => load());
	});

	async function load() {
		loading = true;
		try {
			seeds = await targetsApi.listSeeds(targetId);
		} catch {
			toast.error('Seeds not loaded. Check that the api service is running.');
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
			if (result.added > 0) toast.success(`${result.added} stored`);
			if (!result.rejected.length) open = false;
		} catch {
			toast.error('Seeds not stored.');
		} finally {
			adding = false;
		}
	}

	async function remove(seed: TargetSeed) {
		removing = seed.id;
		try {
			await targetsApi.deleteSeed(targetId, seed.id);
			seeds = seeds.filter((s) => s.id !== seed.id);
		} catch {
			toast.error('Seed not removed.');
		} finally {
			removing = null;
		}
	}
</script>

<Cell id="seeds" title="Seed assets" loading={loading && !seeds.length} class={className}>
	{#snippet tools()}
		<Button
			variant="outline"
			size="sm"
			class="h-7 gap-1 px-2 text-xs"
			onclick={() => (open = true)}
		>
			<Plus class="size-3.5" />
			Add
		</Button>
	{/snippet}
	{#if seeds.length}
		<ScrollArea class={seeds.length > VISIBLE ? 'h-48' : ''}>
			<ul class="flex flex-col">
				{#each seeds as seed (seed.id)}
					<li class="flex items-center gap-2 border-t py-1 first:border-t-0">
						<span class="min-w-0 flex-1 font-mono text-xs break-all">{seed.value}</span>
						{#if seed.kind !== 'host'}
							<Badge variant="outline" class="font-normal">{seed.kind}</Badge>
						{/if}
						<Button
							variant="ghost"
							size="icon"
							class="size-6 shrink-0"
							disabled={removing === seed.id}
							onclick={() => remove(seed)}
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
	{:else}
		<span class="text-sm text-muted-foreground">No seed</span>
	{/if}
	{#snippet footer()}
		<span>{seeds.length.toLocaleString()} stored</span>
	{/snippet}
</Cell>

<Dialog.Root bind:open>
	<Dialog.Content class="flex flex-col gap-0 p-0 sm:max-w-[480px]">
		<Dialog.Header class="p-6 pb-4">
			<Dialog.Title>Add seed assets</Dialog.Title>
			<Dialog.Description>One host name, address or URL per line.</Dialog.Description>
		</Dialog.Header>
		<div class="flex flex-col gap-3 px-6 pb-6">
			<Textarea
				rows={6}
				placeholder="www.example.com"
				bind:value={draft}
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
			<div class="flex justify-end gap-2">
				<Button variant="outline" size="sm" onclick={() => (open = false)}>Cancel</Button>
				<LoadingButton size="sm" loading={adding} disabled={!lines.length} onclick={add}>
					<Plus class="size-3.5" />
					Store
				</LoadingButton>
			</div>
		</div>
	</Dialog.Content>
</Dialog.Root>
