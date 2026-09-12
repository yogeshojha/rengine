<script lang="ts">
	import CheckIcon from '@lucide/svelte/icons/check';
	import { Badge } from '$lib/components/ui/badge';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import Hint from '$lib/components/hint.svelte';
	import { assetIcon } from '$lib/config/bounty-programs';
	import { ScopeState, type BountyScope } from '$lib/types/bounty-program';

	interface Props {
		scope: BountyScope;
		selected: boolean;
		allowOutOfScope: boolean;
		onToggle: (id: string) => void;
	}

	let { scope, selected, allowOutOfScope, onToggle }: Props = $props();

	const Icon = $derived(assetIcon(scope.icon));
	const outOfScope = $derived(scope.scope_state === ScopeState.OutOfScope);
	const selectable = $derived(
		scope.importable && !scope.already_target && (!outOfScope || allowOutOfScope)
	);
</script>

<div
	class="flex items-start gap-3 border-b px-4 py-2.5 last:border-b-0"
	class:opacity-60={outOfScope}
>
	<span class="flex h-5 w-4 shrink-0 items-center justify-center">
		{#if selectable}
			<Checkbox
				checked={selected}
				onCheckedChange={() => onToggle(scope.id)}
				aria-label={`Select ${scope.asset_identifier}`}
			/>
		{:else if scope.already_target}
			<Hint text="Existing target in this project">
				{#snippet child(props)}
					<span {...props} class="flex h-5 items-center">
						<CheckIcon class="size-3.5 text-success" />
					</span>
				{/snippet}
			</Hint>
		{/if}
	</span>

	<span class="flex h-5 shrink-0 items-center">
		<Icon class="size-3.5 text-muted-foreground" />
	</span>

	<span class="flex min-w-0 flex-1 flex-col gap-0.5">
		<span class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
			<span class="font-mono text-xs leading-5 break-all">{scope.asset_identifier}</span>
			{#if outOfScope}
				<Badge variant="outline" class="text-muted-foreground">Out of scope</Badge>
			{/if}
		</span>

		{#if scope.instruction}
			<span class="text-xs leading-5 text-muted-foreground">{scope.instruction}</span>
		{/if}

		<span class="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-2xs text-muted-foreground">
			<span>{scope.asset_type_label}</span>
			{#if scope.max_severity}
				<span>Pays up to {scope.max_severity}</span>
			{/if}
			{#if scope.eligible_for_bounty === false}
				<span>No bounty</span>
			{/if}
			{#if scope.importable && scope.target_value !== scope.asset_identifier}
				<span>Adds as <span class="font-mono">{scope.target_value}</span></span>
			{:else if !scope.importable}
				<span class="text-muted-foreground/70">Not scannable</span>
			{/if}
		</span>
	</span>
</div>
