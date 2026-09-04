<script lang="ts">
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Badge } from '$lib/components/ui/badge';
	import Hint from '$lib/components/hint.svelte';
	import { httpStatusTextClass } from '$lib/utilities/scan-correlation';
	import { locationLabel, originLabel, type VulnerabilityRead } from '$lib/utilities/vulns';
	import { VULN_STATE_LABELS, VulnState } from '$lib/config/vulnerabilities';

	interface Props {
		items: VulnerabilityRead[];
		loading: boolean;
		total: number;
		selectedId: string | null;
		onOpen: (v: VulnerabilityRead) => void;
		onMore: () => void;
	}

	let { items, loading, total, selectedId, onOpen, onMore }: Props = $props();

	interface HostGroup {
		host: string;
		status: number | null;
		title: string | null;
		items: VulnerabilityRead[];
	}

	let groups = $derived.by(() => {
		const out: HostGroup[] = [];
		for (const v of items) {
			const key = originLabel(v);
			let group = out.find((g) => g.host === key);
			if (!group) {
				group = {
					host: key,
					status: v.asset?.status_code ?? null,
					title: v.asset?.title ?? null,
					items: []
				};
				out.push(group);
			}
			group.items.push(v);
		}
		return out;
	});
</script>

<div class="border-t border-border/60 bg-muted/15 pr-4 pl-4 sm:pl-14">
	{#if loading && items.length === 0}
		<div class="flex flex-col gap-2 py-3">
			{#each Array(3) as _, i (i)}
				<Skeleton class="h-6 w-full" />
			{/each}
		</div>
	{:else}
		<div class="flex flex-col divide-y divide-border/50">
			{#each groups as group (group.host)}
				<div class="flex flex-col gap-1 py-2.5">
					<div class="flex items-center gap-2">
						{#if group.status != null}
							<span class="font-mono text-xs tabular-nums {httpStatusTextClass(group.status)}">
								{group.status}
							</span>
						{/if}
						<span class="font-mono text-xs font-medium">{group.host}</span>
						{#if group.title}
							<span class="min-w-0 truncate text-xs text-muted-foreground">{group.title}</span>
						{/if}
					</div>
					<ul class="flex flex-col">
						{#each group.items as v (v.id)}
							{@const reviewed = v.state !== VulnState.OPEN}
							<li>
								<button
									type="button"
									class="group/inst flex w-full items-center gap-2 rounded-sm px-1.5 py-0.5 text-left hover:bg-muted/50 {selectedId ===
									v.id
										? 'bg-primary/5'
										: ''}"
									onclick={() => onOpen(v)}
								>
									<span
										class="min-w-0 flex-1 font-mono text-xs leading-4 wrap-anywhere {reviewed
											? 'text-muted-foreground line-through decoration-border'
											: ''}"
									>
										{locationLabel(v)}
									</span>
									{#if v.matcher_name}
										<span class="shrink-0 font-mono text-[11px] text-muted-foreground">
											{v.matcher_name}
										</span>
									{/if}
									{#if v.extracted_results.length}
										<Badge
											variant="secondary"
											class="max-w-40 px-1 font-mono text-[10px] font-normal"
										>
											<span class="truncate">{v.extracted_results[0]}</span>
										</Badge>
									{/if}
									{#if v.is_new}
										<Badge variant="info" class="px-1 text-[10px] font-normal">new</Badge>
									{/if}
									{#if reviewed}
										<Badge variant="secondary" class="px-1 text-[10px] font-normal">
											{VULN_STATE_LABELS[v.state] ?? v.state}
										</Badge>
									{/if}
									{#if v.url}
										<Hint text="Open in a new tab">
											{#snippet child(props)}
												<Button
													{...props}
													variant="ghost"
													size="icon"
													class="size-6 opacity-0 group-hover/inst:opacity-100 focus-visible:opacity-100"
													href={v.matched_at}
													target="_blank"
													rel="noopener noreferrer"
													onclick={(e: Event) => e.stopPropagation()}
												>
													<ExternalLink class="size-3" />
													<span class="sr-only">Open {v.matched_at}</span>
												</Button>
											{/snippet}
										</Hint>
									{/if}
								</button>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</div>
		{#if total > items.length}
			<div class="py-2">
				<Button variant="ghost" size="sm" class="h-7 text-xs" onclick={onMore}>
					Show {Math.min(total - items.length, 100)} more of {total.toLocaleString()} findings
				</Button>
			</div>
		{/if}
	{/if}
</div>
