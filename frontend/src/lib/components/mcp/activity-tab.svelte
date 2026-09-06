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
			<PanelHead title="Most called" description="Across the calls kept in the trail" />
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
		<PanelHead title="Recent calls" description="The last 100 calls, newest first">
			<Button variant="ghost" size="sm" onclick={() => mcp.loadCalls()}>
				<RefreshCwIcon class="size-4" />
				Refresh
			</Button>
		</PanelHead>

		{#if calls.length === 0}
			<div class="px-5 py-8">
				<EmptyState
					compact
					icon={ActivityIcon}
					title="No calls yet"
					description="Once an agent connects and calls a tool, its activity shows here."
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

	<p class="text-xs text-muted-foreground">
		Calls and sessions are kept in Redis for seven days, not in the database. Restarting Redis
		clears this trail; it does not affect tokens or the server state.
	</p>
</div>
