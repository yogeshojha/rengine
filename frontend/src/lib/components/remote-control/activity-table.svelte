<script lang="ts">
	import { BODY_ROW, HEAD_ROW } from '$lib/components/settings/columns';
	import ActivityIcon from '@lucide/svelte/icons/activity';
	import EmptyState from '$lib/components/empty-state.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { formatMilliseconds } from '$lib/utilities/format';
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
	<div class="px-4 py-10">
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
		<div class={HEAD_ROW} role="row">
			<div class={CALL_COL.time} role="columnheader">Time</div>
			<div class={CALL_COL.chat} role="columnheader">Chat</div>
			<div class={CALL_COL.command} role="columnheader">Command</div>
			<div class={CALL_COL.result} role="columnheader">Result</div>
		</div>
		{#each rows as call, i (call.at + call.tool + i)}
			<div class={BODY_ROW} role="row">
				<div
					class="{CALL_COL.time} text-xs leading-5 text-muted-foreground tabular-nums"
					role="cell"
				>
					{relativeTime(call.at)}
				</div>
				<div class="{CALL_COL.chat} text-sm leading-5 wrap-anywhere" role="cell">
					{chatName(call.token_name)}
				</div>
				<div class="{CALL_COL.command} font-mono text-xs leading-5 wrap-anywhere" role="cell">
					{call.command ?? `/${commandFor(call.tool, commands)}`}
				</div>
				<div class="{CALL_COL.result} items-start gap-2 text-xs leading-5" role="cell">
					<span class="flex h-5 shrink-0 items-center">
						<span
							class="size-1.5 rounded-full {call.ok ? 'bg-success' : 'bg-destructive'}"
							aria-hidden="true"
						></span>
					</span>
					{#if call.ok}
						<span class="text-muted-foreground tabular-nums"
							>{formatMilliseconds(call.duration_ms)}</span
						>
					{:else}
						<span class="text-destructive wrap-anywhere">{call.detail ?? 'Failed'}</span>
					{/if}
				</div>
			</div>
		{/each}
	</div>
{/if}
