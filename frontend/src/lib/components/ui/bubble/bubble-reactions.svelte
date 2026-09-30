<script lang="ts" module>
	import { tv, type VariantProps } from 'tailwind-variants';

	export const bubbleReactionsVariants = tv({
		base: 'rounded-full ring-3 ring-card bg-muted shrink-0 gap-1 px-1.5 py-0.5 has-[button]:p-0 text-sm absolute z-10 flex w-fit items-center justify-center',
		variants: {
			side: {
				top: 'top-0 -translate-y-3/4',
				bottom: 'bottom-0 translate-y-3/4'
			},
			align: {
				start: 'left-3',
				end: 'right-3'
			}
		},
		defaultVariants: {
			side: 'bottom',
			align: 'end'
		}
	});

	export type BubbleReactionsSide = VariantProps<typeof bubbleReactionsVariants>['side'];
	export type BubbleReactionsAlign = VariantProps<typeof bubbleReactionsVariants>['align'];
</script>

<script lang="ts">
	import { cn, type WithElementRef } from '$lib/utils.js';
	import type { HTMLAttributes } from 'svelte/elements';

	let {
		ref = $bindable(null),
		class: className,
		side = 'bottom',
		align = 'end',
		children,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> & {
		side?: BubbleReactionsSide;
		align?: BubbleReactionsAlign;
	} = $props();
</script>

<div
	bind:this={ref}
	data-slot="bubble-reactions"
	data-align={align}
	data-side={side}
	class={cn(bubbleReactionsVariants({ side, align }), className)}
	{...restProps}
>
	{@render children?.()}
</div>
