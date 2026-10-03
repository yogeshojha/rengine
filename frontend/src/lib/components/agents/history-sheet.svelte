<script lang="ts">
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import CallRecord from './call-record.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { callsOf } from '$lib/utilities/mcp';
	import type { McpToken } from '$lib/types/mcp';

	interface Props {
		token: McpToken | null;
		titles: Map<string, string>;
		onOpenChange: (open: boolean) => void;
	}

	let { token, titles, onOpenChange }: Props = $props();

	const calls = $derived(token ? callsOf(mcp.calls, token) : []);
</script>

<Sheet.Root open={token !== null} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-2xl">
		{#if token}
			<Sheet.Header class="border-b px-5 py-4 pr-12">
				<Sheet.Title class="wrap-anywhere">{token.name}</Sheet.Title>
				<Sheet.Description>Recent calls</Sheet.Description>
			</Sheet.Header>
			<ScrollArea class="min-h-0 flex-1">
				{#key token.id}
					<CallRecord {calls} {titles} />
				{/key}
			</ScrollArea>
		{/if}
	</Sheet.Content>
</Sheet.Root>
