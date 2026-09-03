<script lang="ts">
	import * as Select from '$lib/components/ui/select';
	import { cn } from '$lib/utils';

	interface Props {
		pageSize: number;
		onPageSizeChange: (size: number) => void;
		options?: number[];
		class?: string;
	}

	let { pageSize, onPageSizeChange, options, class: className }: Props = $props();

	const DEFAULT_OPTIONS = [
		{ value: '10', label: '10 per page' },
		{ value: '20', label: '20 per page' },
		{ value: '50', label: '50 per page' },
		{ value: '100', label: '100 per page' },
		{ value: '-1', label: 'All' }
	];
	let pageSizeOptions = $derived(
		options ? options.map((n) => ({ value: String(n), label: `${n} per page` })) : DEFAULT_OPTIONS
	);

	let selectedValue = $derived(pageSize === -1 ? '-1' : pageSize.toString());

	const triggerContent = $derived(
		pageSizeOptions.find((opt) => opt.value === selectedValue)?.label ?? '10 per page'
	);

	function handleValueChange(value: string | undefined) {
		if (value) {
			onPageSizeChange(parseInt(value));
		}
	}
</script>

<Select.Root type="single" bind:value={selectedValue} onValueChange={handleValueChange}>
	<Select.Trigger class={cn('h-9 w-[140px]', className)}>
		{triggerContent}
	</Select.Trigger>
	<Select.Content>
		{#each pageSizeOptions as option (option.value)}
			<Select.Item value={option.value} label={option.label}>
				{option.label}
			</Select.Item>
		{/each}
	</Select.Content>
</Select.Root>
