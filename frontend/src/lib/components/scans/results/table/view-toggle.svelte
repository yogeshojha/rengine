<script lang="ts">
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import type { IconComponent } from '$lib/config/icons';

	interface Props {
		value: string;
		icon: IconComponent;
		label: string;
	}

	let { value, icon: Icon, label }: Props = $props();
</script>

<Tooltip.Root>
	<Tooltip.Trigger>
		{#snippet child({ props })}
			<ToggleGroup.Item {...props} {value} aria-label={label} class="h-7 px-2">
				<Icon class="size-3.5" />
			</ToggleGroup.Item>
		{/snippet}
	</Tooltip.Trigger>
	<Tooltip.Content>{label}</Tooltip.Content>
</Tooltip.Root>
