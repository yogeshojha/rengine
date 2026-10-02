<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { VULN_STATE_LABELS } from '$lib/config/vulnerabilities';
	import { cn } from '$lib/utils';

	interface Props {
		state: string;
		class?: string;
	}

	let { state: value, class: className }: Props = $props();
</script>

<Badge variant="outline" class={cn('h-5 px-1.5 text-2xs font-medium', className)}>
	{VULN_STATE_LABELS[value] ?? value}
</Badge>
