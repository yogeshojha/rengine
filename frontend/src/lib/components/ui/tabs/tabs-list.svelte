<script lang="ts" module>
	import { tv, type VariantProps } from 'tailwind-variants';

	export const tabsListVariants = tv({
		base: 'group/tabs-list text-muted-foreground inline-flex h-9 w-fit items-center justify-center rounded-lg p-[3px] data-[variant=line]:rounded-none',
		variants: {
			variant: {
				default: 'bg-muted',
				line: 'gap-1 bg-transparent'
			}
		},
		defaultVariants: {
			variant: 'default'
		}
	});

	export type TabsListVariant = VariantProps<typeof tabsListVariants>['variant'];
</script>

<script lang="ts">
	import { Tabs as TabsPrimitive } from 'bits-ui';
	import { cn } from '$lib/utils.js';

	let {
		ref = $bindable(null),
		variant = 'default',
		class: className,
		...restProps
	}: TabsPrimitive.ListProps & {
		variant?: TabsListVariant;
	} = $props();
</script>

<TabsPrimitive.List
	bind:ref
	data-slot="tabs-list"
	data-variant={variant}
	class={cn(tabsListVariants({ variant }), className)}
	{...restProps}
/>
