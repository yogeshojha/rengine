<script lang="ts">
	import RungMeter from '$lib/components/access/rung-meter.svelte';
	import { MCP_CAPABILITIES, MCP_CAPABILITY_LABELS, ladderLevel } from '$lib/types/mcp';
	import type { ChannelChat } from '$lib/types/remote-control';

	interface Props {
		chat: ChannelChat;
	}

	let { chat }: Props = $props();

	const held = $derived(chat.effective_capabilities.length < chat.capabilities.length);
	const top = $derived(MCP_CAPABILITIES[ladderLevel(chat.effective_capabilities)]);
</script>

<div class="flex flex-col gap-1">
	<RungMeter granted={chat.capabilities} effective={chat.effective_capabilities} class="w-24" />
	<span class="text-2xs {held ? 'text-warning' : 'text-muted-foreground'}">
		{held ? 'Read only' : MCP_CAPABILITY_LABELS[top]}
	</span>
</div>
