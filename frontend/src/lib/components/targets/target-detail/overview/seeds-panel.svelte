<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Switch } from '$lib/components/ui/switch';
	import { Textarea } from '$lib/components/ui/textarea';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Badge } from '$lib/components/ui/badge';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import { targetsApi } from '$lib/api/targets';
	import type { TargetSeed, TargetSeedRejection } from '$lib/types/target';

	interface Props {
		targetId: string;
		seedScans: boolean;
		onToggle: (on: boolean) => void;
	}

	let { targetId, seedScans, onToggle }: Props = $props();

	let seeds = $state<TargetSeed[]>([]);
	let loading = $state(true);
	let adding = $state(false);
	let removing = $state<string | null>(null);
	let draft = $state('');
	let rejected = $state<TargetSeedRejection[]>([]);
	let loadedFor = $state<string | null>(null);

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

<section class="flex flex-col gap-3 border-t py-5">
	<SectionHead title="Seed assets" count={loading ? null : seeds.length}>
		<label class="flex items-center gap-2">
			<Switch
				checked={seedScans}
				onCheckedChange={onToggle}
				aria-label="Seed scans of this target"
			/>
			<span>Seed scans</span>
		</label>
	</SectionHead>

	<p class="text-xs text-muted-foreground">
		{seedScans ? 'Every scan of this target starts from these.' : 'Stored, and not used.'}
	</p>

	{#if loading}
		<Skeleton class="h-10 w-2/3" />
	{:else if seeds.length > 0}
		<ScrollArea class={seeds.length > 8 ? 'h-64' : ''}>
			<div class="flex flex-col">
				{#each seeds as seed (seed.id)}
					<div class="flex items-center gap-2 border-b py-1.5 last:border-b-0">
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
					</div>
				{/each}
			</div>
		</ScrollArea>
	{/if}

	<div class="flex flex-col gap-2">
		<Textarea rows={3} placeholder="www.example.com" bind:value={draft} class="font-mono text-xs" />
		<div class="flex items-center justify-between gap-3">
			<span class="text-2xs text-muted-foreground"> One host name, address or URL per line. </span>
			<LoadingButton size="sm" loading={adding} disabled={!lines.length} onclick={add}>
				<Plus class="size-3.5" />
				Store
			</LoadingButton>
		</div>
	</div>

	{#if rejected.length > 0}
		<div class="flex flex-col gap-1 border-t pt-2">
			{#each rejected as item, i (item.value + i)}
				<div class="flex items-baseline gap-2 text-xs">
					<span class="font-mono break-all text-muted-foreground">{item.value}</span>
					<span class="text-destructive">{item.reason}</span>
				</div>
			{/each}
		</div>
	{/if}
</section>
