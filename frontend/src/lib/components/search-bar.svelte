<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
	import { Separator } from '$lib/components/ui/separator';
	import Spinner from '$lib/components/ui/spinner/spinner.svelte';

	interface Props {
		value: string;
		placeholder?: string;
		label: string;
		busy?: boolean;
		total?: number | null;
		capped?: boolean;
		noun?: string;
		nounPlural?: string;
		mono?: boolean;
		ref?: HTMLInputElement | null;
		onChange: (value: string) => void;
		onSubmit?: (value: string) => void;
	}

	let {
		value,
		placeholder = '',
		label,
		busy = false,
		total = null,
		capped = false,
		noun = 'result',
		nounPlural = 'results',
		mono = false,
		ref = $bindable(null),
		onChange,
		onSubmit
	}: Props = $props();

	const TEXT = 'text-sm leading-6';
	let focused = $state(false);
</script>

<div class="overflow-hidden rounded-t-xl border bg-card">
	<div
		class="flex h-14 items-center gap-3 px-3 transition-colors sm:px-4 {focused
			? 'bg-card'
			: 'bg-muted/30'}"
	>
		<span
			class="flex size-8 shrink-0 items-center justify-center rounded-lg transition-colors {focused
				? 'bg-primary text-primary-foreground shadow-sm'
				: 'bg-background text-muted-foreground ring-1 ring-border'}"
		>
			{#if busy}
				<Spinner class="size-4" />
			{:else}
				<Search class="size-4" />
			{/if}
		</span>

		<input
			bind:this={ref}
			{value}
			{placeholder}
			type="text"
			aria-label={label}
			autocomplete="off"
			autocapitalize="off"
			autocorrect="off"
			spellcheck={false}
			class="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted-foreground {TEXT} {mono
				? 'font-mono'
				: ''}"
			oninput={(e) => onChange(e.currentTarget.value)}
			onkeydown={(e) => {
				if (e.key === 'Escape') {
					onChange('');
					e.currentTarget.blur();
				}
				if (e.key === 'Enter') onSubmit?.(e.currentTarget.value);
			}}
			onfocus={() => (focused = true)}
			onblur={() => (focused = false)}
		/>

		<div class="flex shrink-0 items-center gap-1">
			{#if value}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon"
								class="size-7 text-muted-foreground"
								aria-label="Clear search"
								onclick={() => onChange('')}
							>
								<X class="size-4" />
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>Clear <Kbd>Esc</Kbd></Tooltip.Content>
				</Tooltip.Root>
			{:else if !focused}
				<Kbd class="max-sm:hidden">/</Kbd>
			{/if}
			{#if total !== null}
				<div class="mx-1 flex h-5 items-stretch max-sm:hidden">
					<Separator orientation="vertical" />
				</div>
				<span class="px-1 text-xs text-muted-foreground tabular-nums max-sm:hidden">
					{total.toLocaleString()}{capped ? '+' : ''}
					{total === 1 ? noun : nounPlural}
				</span>
			{/if}
		</div>
	</div>
</div>
