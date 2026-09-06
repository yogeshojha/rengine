<script lang="ts">
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import Undo2 from '@lucide/svelte/icons/undo-2';
	import { toast } from 'svelte-sonner';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { interestApi } from '$lib/api/interest';
	import { interestCatalog } from '$lib/stores/interest-catalog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import type { InterestDismissal } from '$lib/types/interest';

	let rows = $state<InterestDismissal[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	let projectId = $derived(projectsStore.activeProject?.id ?? '');

	$effect(() => {
		void interestCatalog.load();
	});

	$effect(() => {
		const id = projectId;
		if (!id) return;
		void load(id);
	});

	async function load(id: string): Promise<void> {
		loading = true;
		try {
			rows = await interestApi.dismissals(id);
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load dismissals';
		} finally {
			loading = false;
		}
	}

	async function restore(row: InterestDismissal): Promise<void> {
		try {
			await interestApi.restore(row.id);
			rows = rows.filter((r) => r.id !== row.id);
			toast.success(`${row.host} can be flagged again from the next scan`);
		} catch {
			toast.error('Could not restore');
		}
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead
		title="Dismissed"
		description="Assets you marked as not interesting. They stay out of the list on every later scan."
	>
		<span class="tabular-nums">{rows.length}</span>
	</PanelHead>

	{#if loading}
		<div class="flex flex-col gap-2 p-5">
			{#each Array(4) as _, i (i)}
				<Skeleton class="h-9 w-full" />
			{/each}
		</div>
	{:else if error}
		<EmptyState icon={EyeOff} title="Could not load dismissals" description={error} class="py-12" />
	{:else if !rows.length}
		<EmptyState
			icon={EyeOff}
			title="Nothing dismissed"
			description="Dismiss an asset from the Worth a look tab of a scan and it appears here."
			class="py-12"
		/>
	{:else}
		<div class="divide-y">
			{#each rows as row (row.id)}
				<div class="group flex items-center gap-3 px-5 py-2.5 hover:bg-accent/40">
					<span class="min-w-0 flex-1 truncate font-mono text-[12.5px]">{row.host}</span>
					<span class="shrink-0 text-xs text-muted-foreground">
						{row.kind ? interestCatalog.label(row.kind) : 'Every reason'}
					</span>
					<span class="w-28 shrink-0 text-right text-xs text-muted-foreground"
						>{relativeTime(row.created_at)}</span
					>
					<Button
						variant="ghost"
						size="sm"
						class="h-7 shrink-0 opacity-0 group-hover:opacity-100"
						onclick={() => restore(row)}
					>
						<Undo2 class="size-3.5" />
						Restore
					</Button>
				</div>
			{/each}
		</div>
	{/if}
</Card.Root>
