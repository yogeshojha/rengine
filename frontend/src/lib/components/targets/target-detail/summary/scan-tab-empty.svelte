<script lang="ts">
	import * as Empty from '$lib/components/ui/empty';
	import { Button } from '$lib/components/ui/button/index.js';
	import Play from '@lucide/svelte/icons/play';
	import type { IconComponent } from '$lib/config/icons';

	interface Props {
		icon: IconComponent;
		title: string;
		description: string;
		ctaLabel?: string;
		onScan?: () => void;
	}

	let { icon, title, description, ctaLabel = 'Scan target', onScan }: Props = $props();
	const Icon = $derived(icon);
</script>

<Empty.Root class="rounded-lg border border-dashed bg-card/40 py-20">
	<Empty.Header>
		<Empty.Media
			variant="icon"
			class="h-14 w-14 rounded-2xl bg-muted text-muted-foreground/60 [&_svg:not([class*='size-'])]:size-6"
		>
			<Icon />
		</Empty.Media>
		<Empty.Title class="text-sm">{title}</Empty.Title>
		<Empty.Description class="max-w-sm">{description}</Empty.Description>
	</Empty.Header>
	<Empty.Content>
		<Button size="sm" class="gap-2" onclick={onScan}>
			<Play class="h-3.5 w-3.5" />
			{ctaLabel}
		</Button>
	</Empty.Content>
</Empty.Root>
