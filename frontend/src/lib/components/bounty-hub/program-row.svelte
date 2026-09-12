<script lang="ts">
	import BookmarkCheckIcon from '@lucide/svelte/icons/bookmark-check';
	import CheckIcon from '@lucide/svelte/icons/check';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import RadarIcon from '@lucide/svelte/icons/radar';
	import { Badge } from '$lib/components/ui/badge';
	import Hint from '$lib/components/hint.svelte';
	import { SUBMISSION_STATE_LABELS, formatPayout } from '$lib/config/bounty-programs';
	import { formatShortDate } from '$lib/utilities/dates';
	import { ProgramState, SubmissionState, type BountyProgram } from '$lib/types/bounty-program';

	interface Props {
		program: BountyProgram;
		onOpen: (program: BountyProgram) => void;
	}

	let { program, onOpen }: Props = $props();

	const initials = $derived(
		program.name
			.split(/\s+/)
			.slice(0, 2)
			.map((w) => w[0])
			.join('')
			.toUpperCase()
	);
	const isPrivate = $derived(program.program_state === ProgramState.Private);
	const isOpen = $derived(program.submission_state === SubmissionState.Open);
	const stateKnown = $derived(program.submission_state !== SubmissionState.Unknown);
	const payout = $derived(
		formatPayout(program.min_payout, program.max_payout, program.payout_currency)
	);
	const scopeKnown = $derived(program.scopes_synced_at !== null);
	const scopeTotal = $derived(program.in_scope_count + program.out_of_scope_count);
</script>

<button
	type="button"
	onclick={() => onOpen(program)}
	class="group flex w-full items-center gap-3 border-b px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-muted/40"
>
	<span
		class="flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-md border bg-muted/50 text-2xs font-semibold text-muted-foreground"
	>
		{#if program.profile_picture}
			<img src={program.profile_picture} alt="" class="size-full object-cover" loading="lazy" />
		{:else}
			{initials}
		{/if}
	</span>

	<span class="flex min-w-0 flex-1 flex-col gap-1">
		<span class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
			<span class="truncate text-sm font-medium">{program.name}</span>
			<span class="truncate font-mono text-xs text-muted-foreground">@{program.handle}</span>
			{#if program.bookmarked}
				<Hint text="Bookmarked on HackerOne">
					{#snippet child(props)}
						<span {...props} class="flex h-4 items-center">
							<BookmarkCheckIcon class="size-3.5 text-warning" />
						</span>
					{/snippet}
				</Hint>
			{/if}
		</span>

		<span class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
			{#if !scopeKnown}
				<span class="text-muted-foreground/70">Scope not fetched</span>
			{:else if scopeTotal === 0}
				<span class="text-muted-foreground/70">No structured scope</span>
			{:else}
				<span class="tabular-nums">
					{program.in_scope_count} in scope
				</span>
				{#if program.out_of_scope_count > 0}
					<span class="tabular-nums">{program.out_of_scope_count} out of scope</span>
				{/if}
				<span class="tabular-nums">
					{program.importable_count} scannable
				</span>
			{/if}
			<span class="text-muted-foreground/70">{program.platform_label}</span>
			{#if program.started_accepting_at}
				<span>Since {formatShortDate(program.started_accepting_at)}</span>
			{/if}
			{#if program.safe_harbor}
				<span class="capitalize">{program.safe_harbor} safe harbor</span>
			{/if}
		</span>
	</span>

	<span class="flex shrink-0 items-center gap-1.5">
		{#if program.watched}
			<Badge variant="info" class="gap-1">
				<RadarIcon class="size-3" />
				Watching
			</Badge>
		{/if}
		{#if program.imported_count > 0}
			<Badge variant="success" class="gap-1">
				<CheckIcon class="size-3" />
				{program.imported_count}
			</Badge>
		{/if}
		{#if isPrivate}
			<Badge variant="info">{program.raw_state_label}</Badge>
		{:else if program.joined}
			<Badge variant="outline" class="text-muted-foreground">Joined</Badge>
		{/if}
		{#if payout}
			<Badge variant="outline" class="tabular-nums">{payout}</Badge>
		{/if}
		<Badge variant={program.offers_bounties ? 'default' : 'secondary'}>
			{program.offers_bounties ? 'Bounty' : 'VDP'}
		</Badge>
		{#if stateKnown && !isOpen}
			<Badge variant="outline" class="text-muted-foreground">
				{SUBMISSION_STATE_LABELS[program.submission_state]}
			</Badge>
		{/if}
		<ChevronRightIcon
			class="size-4 text-muted-foreground/50 transition-transform group-hover:translate-x-0.5"
		/>
	</span>
</button>
