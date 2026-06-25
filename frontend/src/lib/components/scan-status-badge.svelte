<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { cn } from '$lib/utils.js';
	import { scanStatusVariant, scanStatusIcon, SCAN_STATUS_LABEL } from '$lib/utilities/scan-status';
	import type { ScanStatus } from '$lib/types/scan';

	interface Props {
		status: ScanStatus;
		class?: string;
	}

	let { status, class: className }: Props = $props();

	const Icon = $derived(scanStatusIcon(status));
</script>

<Badge variant={scanStatusVariant(status)} class={cn('gap-1 font-normal', className)}>
	<Icon class="h-3 w-3 {status === 'running' ? 'animate-spin' : ''}" />
	{SCAN_STATUS_LABEL[status]}
</Badge>
