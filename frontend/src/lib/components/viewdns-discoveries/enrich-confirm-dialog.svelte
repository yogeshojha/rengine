<script lang="ts">
	import type { DiscoverySourceType } from '$lib/types/viewdns';
	import { DISCOVERY_SOURCE_LABELS } from '$lib/types/viewdns';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import Zap from '@lucide/svelte/icons/zap';

	interface Props {
		open: boolean;
		source: DiscoverySourceType | null;
		queryValue: string;
		isEnriching?: boolean;
		onOpenChange: (open: boolean) => void;
		onConfirm: () => void;
	}

	let {
		open = $bindable(),
		source,
		queryValue,
		isEnriching = false,
		onOpenChange,
		onConfirm
	}: Props = $props();

	let sourceLabel = $derived(source ? DISCOVERY_SOURCE_LABELS[source] : 'ViewDNS');
</script>

<AlertDialog.Root bind:open {onOpenChange}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title class="flex items-center gap-2">
				<Zap class="h-5 w-5 text-muted-foreground" />
				Enrich {sourceLabel}?
			</AlertDialog.Title>
			<AlertDialog.Description>
				<span class="block mb-2">
					This will query ViewDNS.info for
					<span class="font-mono text-foreground">{queryValue}</span>
					and use <span class="font-semibold text-foreground">1 API credit</span>
					from the ViewDNS quota.
				</span>
				<span class="block text-xs text-muted-foreground">
					Results will be cached for 7 days. Subsequent views are free.
				</span>
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel disabled={isEnriching}>Cancel</AlertDialog.Cancel>
			<AlertDialog.Action onclick={onConfirm} disabled={isEnriching}>
				{#if isEnriching}
					Enriching…
				{:else}
					Enrich
				{/if}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
