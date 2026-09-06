<script lang="ts">
	import * as Card from '$lib/components/ui/card/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import ActivityIcon from '@lucide/svelte/icons/activity';
	import PanelHead from '$lib/components/panel-head.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { relativeTime } from '$lib/utilities/dates';

	const calls = $derived(mcp.calls);

	const failed = $derived(calls.filter((c) => !c.ok).length);
	const slowest = $derived(calls.reduce((n, c) => Math.max(n, c.duration_ms), 0));

	const byTool = $derived(
		Object.entries(
			calls.reduce<Record<string, number>>((acc, call) => {
				acc[call.tool] = (acc[call.tool] ?? 0) + 1;
				return acc;
			}, {})
		)
			.sort((a, b) => b[1] - a[1])
			.slice(0, 6)
	);
</script>

<div class="space-y-6">
	{#if byTool.length}
		<Card.Root class="gap-0 py-0">
			<PanelHead title="Most called">
				<span class="tabular-nums"
					>{byTool.length} of {new Set(calls.map((c) => c.tool)).size} tools</span
				>
			</PanelHead>
			<div class="divide-y">
				{#each byTool as [tool, count] (tool)}
					{@const share = Math.round((count / calls.length) * 100)}
					<div class="flex items-center gap-3 px-5 py-2.5">
						<span class="w-56 shrink-0 font-mono text-sm">{tool}</span>
						<div class="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
							<div class="h-full rounded-full bg-chart-1" style="width: {share}%"></div>
						</div>
						<span class="w-12 shrink-0 text-right font-mono text-xs text-muted-foreground">
							{count}
						</span>
					</div>
				{/each}
			</div>
		</Card.Root>
	{/if}

	<Card.Root class="gap-0 py-0">
		<PanelHead title="Recent calls">
			<span class="tabular-nums">{calls.length}</span>
			{#if failed}
				<span class="flex items-center gap-1.5 tabular-nums text-destructive">
					<span class="size-1.5 rounded-full bg-destructive" aria-hidden="true"></span>
					{failed} failed
				</span>
			{/if}
			{#if slowest}
				<span class="tabular-nums">{slowest}ms slowest</span>
			{/if}
			<Button variant="ghost" size="icon" class="size-7" onclick={() => mcp.loadCalls()}>
				<RefreshCwIcon class="size-4" />
				<span class="sr-only">Refresh</span>
			</Button>
		</PanelHead>

		{#if calls.length === 0}
			<div class="px-5 py-8">
				<EmptyState
					compact
					icon={ActivityIcon}
					title="No calls yet"
					description="Tool calls appear here once an agent connects."
				/>
			</div>
		{:else}
			<div class="divide-y">
				{#each calls as call, index (call.at + call.tool + index)}
					<div class="flex flex-wrap items-center gap-x-3 gap-y-1 px-5 py-2.5">
						<span class="size-1.5 shrink-0 rounded-full {call.ok ? 'bg-success' : 'bg-destructive'}"
						></span>
						<span class="font-mono text-sm">{call.tool}</span>
						<span class="text-xs text-muted-foreground">
							{call.client} &middot; <span class="font-mono">{call.token_name}</span>
						</span>
						<span class="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
							<span class="font-mono">{call.duration_ms}ms</span>
							<span>{relativeTime(call.at)}</span>
						</span>
						{#if !call.ok && call.detail}
							<p class="w-full text-xs text-destructive">{call.detail}</p>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</Card.Root>
</div>
