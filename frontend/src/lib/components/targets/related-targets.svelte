<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { ROUTES } from '$lib/config/routes';
	import { RELATION_HELP } from '$lib/config/relations';
	import type { RelatedTarget } from '$lib/types/relations';

	interface Props {
		relations: RelatedTarget[];
		kinds?: string[];
		title?: string;
	}

	let { relations, kinds, title = 'Shared with' }: Props = $props();

	let rows = $derived(
		relations
			.map((r) => ({
				...r,
				reasons: kinds ? r.reasons.filter((x) => kinds.includes(x.kind)) : r.reasons
			}))
			.filter((r) => r.reasons.length > 0)
	);
</script>

{#if rows.length}
	<section class="flex flex-col gap-2">
		<h4 class="text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase">
			{title}
		</h4>
		{#each rows as row (row.target_id)}
			<div class="grid grid-cols-1 gap-x-3 gap-y-1 sm:grid-cols-[11rem_minmax(0,1fr)]">
				<a
					href={ROUTES.target(row.target_id)}
					class="truncate font-mono text-sm hover:text-primary"
				>
					{row.target_value}
				</a>
				<span class="flex flex-wrap items-start gap-1.5">
					{#each row.reasons as r (r.kind + r.value)}
						<Hint text="{RELATION_HELP[r.kind] ?? r.label}. {r.detail || r.value}">
							{#snippet child(props)}
								<span {...props} class="inline-flex">
									<Badge variant="secondary" class="h-6 font-normal">
										{r.detail || r.label}
									</Badge>
								</span>
							{/snippet}
						</Hint>
					{/each}
				</span>
			</div>
		{/each}
	</section>
{/if}
