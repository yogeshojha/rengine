<script lang="ts">
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { Button } from '$lib/components/ui/button';
	import { cn } from '$lib/utils';

	interface Props {
		/** Sections of the page that did not load, e.g. ["Surface", "Runs"]. */
		sections: string[];
		busy?: boolean;
		onRetry: () => void;
		class?: string;
	}

	let { sections, busy = false, onRetry, class: className }: Props = $props();
</script>

<!-- one notice, one Retry, for every part of a page that did not load -->
<div
	role="status"
	class={cn(
		'flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-dashed px-4 py-2.5 text-sm text-muted-foreground',
		className
	)}
>
	<TriangleAlert class="size-4 shrink-0 text-warning" strokeWidth={1.5} />
	<span class="min-w-0">{sections.join(', ')} not loaded.</span>
	<Button variant="outline" size="sm" class="ml-auto" disabled={busy} onclick={onRetry}>
		<RefreshCw class="size-4 {busy ? 'animate-spin' : ''}" />
		Retry
	</Button>
</div>
