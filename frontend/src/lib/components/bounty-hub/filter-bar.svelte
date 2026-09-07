<script lang="ts">
	import SearchIcon from '@lucide/svelte/icons/search';
	import XIcon from '@lucide/svelte/icons/x';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import * as Select from '$lib/components/ui/select';
	import { Toggle } from '$lib/components/ui/toggle';
	import { PROGRAM_SORTS } from '$lib/config/bounty-programs';
	import { SELECT_NONE } from '$lib/constants';
	import {
		ProgramState,
		SubmissionState,
		type BountyProgramFilters
	} from '$lib/types/bounty-program';

	interface Props {
		filters: BountyProgramFilters;
		onChange: (next: BountyProgramFilters) => void;
	}

	let { filters, onChange }: Props = $props();

	const REWARD = [
		{ value: SELECT_NONE, label: 'Bounty and VDP' },
		{ value: 'bounty', label: 'Pays a bounty' },
		{ value: 'vdp', label: 'VDP only' }
	];
	const STATE = [
		{ value: SELECT_NONE, label: 'Public and private' },
		{ value: ProgramState.Public, label: 'Public' },
		{ value: ProgramState.Private, label: 'Private' }
	];
	const SUBMISSION = [
		{ value: SELECT_NONE, label: 'Any state' },
		{ value: SubmissionState.Open, label: 'Accepting reports' },
		{ value: SubmissionState.Paused, label: 'Paused' },
		{ value: SubmissionState.Closed, label: 'Closed' }
	];
	const SCOPE = [
		{ value: SELECT_NONE, label: 'Any scope' },
		{ value: 'importable', label: 'Has scannable assets' },
		{ value: 'none', label: 'No scope recorded' }
	];

	const rewardValue = $derived(
		filters.bounty === true ? 'bounty' : filters.bounty === false ? 'vdp' : SELECT_NONE
	);

	function patch(next: Partial<BountyProgramFilters>) {
		onChange({ ...filters, ...next });
	}

	function label(options: { value: string; label: string }[], value: string): string {
		return options.find((o) => o.value === value)?.label ?? options[0].label;
	}

	const active = $derived(
		Boolean(
			filters.q ||
			filters.state ||
			filters.submission ||
			filters.bounty != null ||
			filters.bookmarked ||
			filters.scope
		)
	);
</script>

<div class="flex flex-wrap items-center gap-2">
	<div class="relative min-w-56 flex-1">
		<SearchIcon
			class="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
		/>
		<Input
			value={filters.q ?? ''}
			oninput={(e) => patch({ q: e.currentTarget.value })}
			placeholder="Search programs"
			class="pl-8"
		/>
	</div>

	<Select.Root
		type="single"
		value={filters.state ?? SELECT_NONE}
		onValueChange={(v) => patch({ state: v === SELECT_NONE ? null : (v as ProgramState) })}
	>
		<Select.Trigger class="w-44">{label(STATE, filters.state ?? SELECT_NONE)}</Select.Trigger>
		<Select.Content>
			{#each STATE as option (option.value)}
				<Select.Item value={option.value}>{option.label}</Select.Item>
			{/each}
		</Select.Content>
	</Select.Root>

	<Select.Root
		type="single"
		value={rewardValue}
		onValueChange={(v) => patch({ bounty: v === SELECT_NONE ? null : v === 'bounty' })}
	>
		<Select.Trigger class="w-40">{label(REWARD, rewardValue)}</Select.Trigger>
		<Select.Content>
			{#each REWARD as option (option.value)}
				<Select.Item value={option.value}>{option.label}</Select.Item>
			{/each}
		</Select.Content>
	</Select.Root>

	<Select.Root
		type="single"
		value={filters.submission ?? SELECT_NONE}
		onValueChange={(v) => patch({ submission: v === SELECT_NONE ? null : (v as SubmissionState) })}
	>
		<Select.Trigger class="w-44">
			{label(SUBMISSION, filters.submission ?? SELECT_NONE)}
		</Select.Trigger>
		<Select.Content>
			{#each SUBMISSION as option (option.value)}
				<Select.Item value={option.value}>{option.label}</Select.Item>
			{/each}
		</Select.Content>
	</Select.Root>

	<Select.Root
		type="single"
		value={filters.scope ?? SELECT_NONE}
		onValueChange={(v) => patch({ scope: v === SELECT_NONE ? null : (v as 'importable' | 'none') })}
	>
		<Select.Trigger class="w-48">{label(SCOPE, filters.scope ?? SELECT_NONE)}</Select.Trigger>
		<Select.Content>
			{#each SCOPE as option (option.value)}
				<Select.Item value={option.value}>{option.label}</Select.Item>
			{/each}
		</Select.Content>
	</Select.Root>

	<Toggle
		pressed={filters.joined === true}
		onPressedChange={(v) => patch({ joined: v ? true : null })}
		variant="outline"
		size="sm"
		class="h-9"
	>
		Joined
	</Toggle>

	<Toggle
		pressed={filters.bookmarked === true}
		onPressedChange={(v) => patch({ bookmarked: v ? true : null })}
		variant="outline"
		size="sm"
		class="h-9"
	>
		Bookmarked
	</Toggle>

	<Select.Root
		type="single"
		value={filters.sort ?? 'age'}
		onValueChange={(v) => patch({ sort: v })}
	>
		<Select.Trigger class="w-36">
			{PROGRAM_SORTS.find((s) => s.value === (filters.sort ?? 'age'))?.label}
		</Select.Trigger>
		<Select.Content>
			{#each PROGRAM_SORTS as option (option.value)}
				<Select.Item value={option.value}>{option.label}</Select.Item>
			{/each}
		</Select.Content>
	</Select.Root>

	{#if active}
		<Button
			variant="ghost"
			size="sm"
			class="h-9"
			onclick={() =>
				onChange({
					q: '',
					state: null,
					submission: null,
					bounty: null,
					bookmarked: null,
					joined: null,
					scope: null,
					sort: filters.sort
				})}
		>
			<XIcon class="mr-1 size-3.5" />
			Clear
		</Button>
	{/if}
</div>
