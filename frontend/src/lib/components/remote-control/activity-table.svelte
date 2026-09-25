<script lang="ts">
	import ActivityIcon from '@lucide/svelte/icons/activity';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { durationLabel } from '$lib/utilities/mcp';
	import {
		chatName,
		commandFor,
		type ChannelCall,
		type ChannelCommand
	} from '$lib/types/remote-control';
	import { CALL_COL } from './columns';

	interface Props {
		calls: ChannelCall[];
		commands: ChannelCommand[];
	}

	let { calls, commands }: Props = $props();

	let failedOnly = $state(false);

	const failed = $derived(calls.filter((c) => !c.ok));
	const rows = $derived(failedOnly ? failed : calls);
	const FILTER =
		'inline-flex h-7 items-center gap-1.5 rounded-md border px-2.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none';
</script>

{#if !calls.length}
	<div class="py-10">
		<EmptyState compact icon={ActivityIcon} title="No commands" />
	</div>
{:else}
	<div class="flex items-center gap-1.5 border-b px-4 py-2.5">
		{#each [{ on: false, label: 'All', n: calls.length }, { on: true, label: 'Failed', n: failed.length }] as f (f.label)}
			<button
				type="button"
				class="{FILTER} {failedOnly === f.on
					? 'border-foreground/40 bg-muted'
					: 'border-border hover:border-foreground/30'}"
				aria-pressed={failedOnly === f.on}
				onclick={() => (failedOnly = f.on)}
			>
				<span class="text-muted-foreground">{f.label}</span>
				<span class="font-mono font-semibold tabular-nums {f.on && f.n ? 'text-destructive' : ''}"
					>{f.n}</span
				>
			</button>
		{/each}
	</div>

	<div class="@container/calls w-full" role="table" aria-label="Commands">
		<div
			class="flex items-center gap-4 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
			role="row"
		>
			<div class={CALL_COL.time}>Time</div>
			<div class={CALL_COL.chat}>Chat</div>
			<div class={CALL_COL.command}>Command</div>
			<div class={CALL_COL.result}>Result</div>
		</div>
		{#each rows as call, i (call.at + call.tool + i)}
			<div
				class="flex items-center gap-4 border-b border-border/60 px-4 py-2 last:border-b-0"
				role="row"
			>
				<div class="{CALL_COL.time} text-xs leading-5 text-muted-foreground tabular-nums">
					{relativeTime(call.at)}
				</div>
				<div class="{CALL_COL.chat} truncate text-sm leading-5">{chatName(call.token_name)}</div>
				<div class="{CALL_COL.command} font-mono text-xs leading-5 wrap-anywhere">
					{call.command ?? `/${commandFor(call.tool, commands)}`}
				</div>
				<div class="{CALL_COL.result} items-start gap-2 text-xs leading-5">
					<span class="flex h-5 shrink-0 items-center">
						<span
							class="size-1.5 rounded-full {call.ok ? 'bg-success' : 'bg-destructive'}"
							aria-hidden="true"
						></span>
					</span>
					{#if call.ok}
						<span class="text-muted-foreground tabular-nums">{durationLabel(call.duration_ms)}</span
						>
					{:else}
						<span class="text-destructive wrap-anywhere">{call.detail ?? 'Failed'}</span>
					{/if}
				</div>
			</div>
		{/each}
	</div>
{/if}
