<script lang="ts">
	import ActivityIcon from '@lucide/svelte/icons/activity';
	import SectionHead from '$lib/components/section-head.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { durationLabel } from '$lib/utilities/mcp';
	import { chatName, commandFor } from '$lib/types/remote-control';
	import type { ChannelCall, ChannelCommand } from '$lib/types/remote-control';

	interface Props {
		calls: ChannelCall[];
		commands: ChannelCommand[];
	}

	let { calls, commands }: Props = $props();

	const failed = $derived(calls.filter((c) => !c.ok).length);
</script>

{#if !calls.length}
	<div class="py-5">
		<EmptyState compact icon={ActivityIcon} title="No commands yet" />
	</div>
{:else}
	<section class="flex flex-col gap-3 py-5">
		<SectionHead title="Recent commands" count={calls.length}>
			{#if failed}
				<span class="flex items-center gap-1.5 tabular-nums text-destructive">
					<span class="size-1.5 rounded-full bg-destructive" aria-hidden="true"></span>
					{failed} failed
				</span>
			{/if}
		</SectionHead>
		<ul class="divide-y rounded-md border">
			{#each calls as call, i (call.at + call.tool + i)}
				<li class="flex items-start gap-3 px-4 py-2.5">
					<span class="flex h-5 shrink-0 items-center">
						<span
							class="size-2 rounded-full {call.ok ? 'bg-success' : 'bg-destructive'}"
							aria-hidden="true"
						></span>
					</span>
					<div class="min-w-0 flex-1">
						<div class="flex flex-wrap items-center gap-x-2 leading-5">
							<span class="text-sm font-medium">{chatName(call.token_name)}</span>
							<code class="font-mono text-xs">/{commandFor(call.tool, commands)}</code>
							<span class="text-xs text-muted-foreground">{relativeTime(call.at)}</span>
						</div>
						{#if !call.ok && call.detail}
							<div class="text-xs text-destructive wrap-anywhere">{call.detail}</div>
						{/if}
					</div>
					<span class="shrink-0 text-xs text-muted-foreground tabular-nums">
						{durationLabel(call.duration_ms)}
					</span>
				</li>
			{/each}
		</ul>
	</section>
{/if}
