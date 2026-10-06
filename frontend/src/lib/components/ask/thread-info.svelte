<script lang="ts">
	import Info from '@lucide/svelte/icons/info';
	import * as Popover from '$lib/components/ui/popover';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { BlockKind } from '$lib/config/ask';
	import { formatCost } from '$lib/config/ai';
	import { surfaceSpec } from '$lib/config/surface';
	import { scopeCount, scopeLabel } from './link-scope';
	import type { AnswerBlock, BlockData, EstateThread } from '$lib/types/ask';

	interface Props {
		thread: EstateThread;
		blocks: AnswerBlock[];
		datas: Map<string, BlockData>;
		model: string | null;
		onRef: (id: string) => void;
	}

	let { thread, blocks, datas, model, onRef }: Props = $props();

	let open = $state(false);

	function label(b: AnswerBlock): string {
		if (b.kind === BlockKind.CVE) return b.cve ?? '';
		if (b.title) return b.title;
		const spec = surfaceSpec(b.dimension ?? '');
		return (b.total === 1 ? spec?.noun : spec?.nounPlural) ?? '';
	}

	function pick(id: string) {
		open = false;
		onRef(id);
	}
</script>

<Popover.Root bind:open>
	<Popover.Trigger>
		{#snippet child({ props })}
			<Button
				{...props}
				variant="ghost"
				size="icon-sm"
				class="size-8 text-muted-foreground"
				aria-label="Thread details"
			>
				<Info class="size-4" />
			</Button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content class="w-80 p-0" align="end">
		<dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1.5 px-3 py-3 text-xs">
			<dt class="text-muted-foreground">Scope</dt>
			<dd class="m-0 truncate">{scopeLabel(thread.scope)}</dd>
			{#if scopeCount(thread.scope)}
				<dt class="text-muted-foreground">Targets</dt>
				<dd class="m-0 tabular-nums">{thread.scope.targets}</dd>
			{/if}
			{#if model}
				<dt class="text-muted-foreground">Model</dt>
				<dd class="m-0 truncate font-mono">{model}</dd>
			{/if}
			{#if thread.cost_usd}
				<dt class="text-muted-foreground">Spent</dt>
				<dd class="m-0 tabular-nums">{formatCost(thread.cost_usd)}</dd>
			{/if}
		</dl>
		{#if blocks.length}
			<div class="border-t">
				<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-64">
					<ul class="flex flex-col p-1">
						{#each blocks as b (b.id)}
							{@const d = datas.get(b.id)}
							{@const total = d?.total ?? b.total}
							<li>
								<button
									type="button"
									class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs hover:bg-muted"
									onclick={() => pick(b.id)}
								>
									<span class="font-mono text-2xs font-semibold text-primary">{b.id}</span>
									<span class="min-w-0 flex-1 truncate">{label(b)}</span>
									{#if total != null && b.kind !== BlockKind.CVE}
										<span class="tabular-nums"
											>{total.toLocaleString()}{(d?.capped ?? b.capped) ? '+' : ''}</span
										>
									{/if}
								</button>
							</li>
						{/each}
					</ul>
				</ScrollArea>
			</div>
		{/if}
	</Popover.Content>
</Popover.Root>
