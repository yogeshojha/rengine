<script lang="ts">
	import Cell from '$lib/components/cell.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { ROUTES } from '$lib/config/routes';
	import type { ProgramMatch } from '$lib/types/relations';

	interface Props {
		programs: ProgramMatch[];
		class?: string;
	}

	let { programs, class: className = '' }: Props = $props();

	let inScope = $derived(programs.filter((p) => p.in_scope).length);
</script>

<Cell
	id="programs"
	title="Programs"
	description="Bounty programs naming this target"
	href={ROUTES.bountyHub()}
	hrefLabel="Bounty Hub"
	class={className}
>
	<ul class="flex flex-col">
		{#each programs as p (p.program_id)}
			<li class="border-t first:border-t-0">
				<a
					href={ROUTES.bountyHub(p.handle, p.platform)}
					class="-mx-2 flex min-w-0 flex-col gap-0.5 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-muted/40"
				>
					<span class="flex min-w-0 items-center gap-2">
						<span class="truncate font-medium">{p.name}</span>
						<span class="text-xs text-muted-foreground">{p.platform}</span>
						<span class="ml-auto flex shrink-0 items-center gap-1">
							{#if !p.in_scope}
								<Badge variant="secondary" class="px-1.5 py-0 text-2xs">Out of scope</Badge>
							{:else if p.eligible_for_bounty}
								<Badge variant="success" class="px-1.5 py-0 text-2xs">Bounty</Badge>
							{/if}
						</span>
					</span>
					<span class="truncate font-mono text-xs text-muted-foreground">{p.scope_identifier}</span>
				</a>
			</li>
		{/each}
	</ul>
	{#snippet footer()}
		<span>{inScope} in scope · {programs.length - inScope} out of scope</span>
	{/snippet}
</Cell>
