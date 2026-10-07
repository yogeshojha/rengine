<script lang="ts">
	import CheckIcon from '@lucide/svelte/icons/check';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { Button } from '$lib/components/ui/button/index.js';

	interface Props {
		value: string;
		id?: string;
		disabled?: boolean;
		onChange: (zone: string) => void;
	}

	let { value, id, disabled = false, onChange }: Props = $props();

	let open = $state(false);

	const zones = $derived.by(() => {
		const all = ['UTC', ...Intl.supportedValuesOf('timeZone').filter((z) => z !== 'UTC')];
		return value && !all.includes(value) ? [value, ...all] : all;
	});

	function pick(zone: string) {
		open = false;
		if (zone !== value) onChange(zone);
	}
</script>

<Popover.Root bind:open>
	<Popover.Trigger {disabled}>
		{#snippet child({ props })}
			<Button
				{...props}
				{id}
				variant="outline"
				role="combobox"
				aria-expanded={open}
				class="h-9 w-60 justify-between font-normal"
			>
				<span class="truncate">{value}</span>
				<ChevronsUpDownIcon class="size-4 shrink-0 text-muted-foreground" />
			</Button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content class="w-72 p-0" align="end">
		<Command.Root>
			<Command.Input placeholder="Search time zones" />
			<Command.List class="max-h-72">
				<Command.Empty>No time zone</Command.Empty>
				<Command.Group>
					{#each zones as zone (zone)}
						<Command.Item value={zone} onSelect={() => pick(zone)}>
							<span class="flex-1 truncate">{zone}</span>
							{#if zone === value}
								<CheckIcon class="size-4 text-primary" />
							{/if}
						</Command.Item>
					{/each}
				</Command.Group>
			</Command.List>
		</Command.Root>
	</Popover.Content>
</Popover.Root>
