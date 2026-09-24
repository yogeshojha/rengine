<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';

	let { builtin }: { builtin: boolean } = $props();
</script>

{#if builtin}
	<Badge variant="secondary" class="text-2xs font-normal">Default</Badge>
{:else}
	<Badge variant="info" class="text-2xs font-normal">Custom</Badge>
{/if}
