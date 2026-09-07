<script lang="ts">
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { SvelteSet } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as ScrollArea from '$lib/components/ui/scroll-area';
	import * as Sheet from '$lib/components/ui/sheet';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Switch } from '$lib/components/ui/switch';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ImportDialog from './import-dialog.svelte';
	import ScopeRow from './scope-row.svelte';
	import { bountyProgramsApi } from '$lib/api/bounty-programs';
	import {
		SOURCE_NOTES,
		SUBMISSION_STATE_LABELS,
		formatPayout,
		platformUrl
	} from '$lib/config/bounty-programs';
	import { formatShortDate } from '$lib/utilities/dates';
	import {
		ProgramState,
		ScopeState,
		SubmissionState,
		type BountyProgram,
		type BountyProgramDetail
	} from '$lib/types/bounty-program';

	interface Props {
		program: BountyProgram | null;
		projectId: string | undefined;
		open: boolean;
		onOpenChange: (open: boolean) => void;
		onImported: () => void;
	}

	let { program, projectId, open, onOpenChange, onImported }: Props = $props();

	let detail = $state<BountyProgramDetail | null>(null);
	let loading = $state(false);
	let importing = $state(false);
	let syncing = $state(false);
	let tab = $state<string>('all');
	let selected = new SvelteSet<string>();
	let showOutOfScope = $state(false);
	let importOpen = $state(false);

	async function load(handle: string, platform: string) {
		loading = true;
		try {
			detail = await bountyProgramsApi.detail(handle, projectId, null, platform);
			selected.clear();
			for (const s of detail.scopes) {
				if (s.importable && !s.already_target && s.scope_state === ScopeState.InScope) {
					selected.add(s.id);
				}
			}
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Could not load the program');
			detail = null;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		const handle = program?.handle;
		const platform = program?.platform;
		if (!open || !handle || !platform) return;
		tab = 'all';
		showOutOfScope = false;
		void load(handle, platform);
	});

	const scopes = $derived(detail?.scopes ?? []);
	const payout = $derived(
		program ? formatPayout(program.min_payout, program.max_payout, program.payout_currency) : null
	);
	const visible = $derived(tab === 'all' ? scopes : scopes.filter((s) => s.scope_state === tab));
	const counts = $derived({
		all: scopes.length,
		[ScopeState.InScope]: detail?.in_scope_count ?? 0,
		[ScopeState.OutOfScope]: detail?.out_of_scope_count ?? 0
	});
	const selectedOutOfScope = $derived(
		scopes.filter((s) => selected.has(s.id) && s.scope_state === ScopeState.OutOfScope).length
	);
	const outOfScopeImportable = $derived(
		scopes.filter(
			(s) => s.scope_state === ScopeState.OutOfScope && s.importable && !s.already_target
		).length
	);
	const unreachableEntries = $derived(Object.entries(detail?.unreachable ?? {}));
	const unreachableTotal = $derived(unreachableEntries.reduce((n, [, v]) => n + v, 0));

	function toggle(id: string) {
		if (selected.has(id)) selected.delete(id);
		else selected.add(id);
	}

	function setAllowOutOfScope(value: boolean) {
		showOutOfScope = value;
		if (value) return;
		for (const s of scopes) {
			if (s.scope_state === ScopeState.OutOfScope) selected.delete(s.id);
		}
	}

	function selectAllVisible() {
		for (const s of visible) {
			if (!s.importable || s.already_target) continue;
			if (s.scope_state === ScopeState.OutOfScope && !showOutOfScope) continue;
			selected.add(s.id);
		}
	}

	async function runImport(options: {
		groupByProgram: boolean;
		organizationName: string;
		tags: string[];
	}) {
		if (!program || !projectId || selected.size === 0) return;
		importing = true;
		try {
			const result = await bountyProgramsApi.importScopes(
				program.handle,
				projectId,
				[...selected],
				selectedOutOfScope > 0,
				options.groupByProgram,
				options.organizationName,
				options.tags,
				program.platform
			);
			const created = result.created.length;
			const grouped = result.organization ? ` under ${result.organization.name}` : '';
			toast.success(
				created > 0
					? `Added ${created} ${created === 1 ? 'target' : 'targets'}${grouped}`
					: `Every selected asset is already a target${grouped}`
			);
			importOpen = false;
			await load(program.handle, program.platform);
			onImported();
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Could not add the targets');
		} finally {
			importing = false;
		}
	}

	async function refreshScope() {
		if (!program) return;
		syncing = true;
		try {
			await bountyProgramsApi.syncProgram(program.handle, program.platform);
			toast.success(
				`Refreshing scope from ${program.platform_label}. Reopen the program in a moment.`
			);
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Could not refresh the scope');
		} finally {
			syncing = false;
		}
	}
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content class="flex w-full flex-col gap-0 p-0 sm:max-w-2xl">
		{#if program}
			<Sheet.Header class="gap-2 border-b p-4">
				<Sheet.Title class="flex flex-wrap items-center gap-2">
					<span class="min-w-0 truncate">{program.name}</span>
					{#if program.program_state === ProgramState.Private}
						<Badge variant="info">{program.raw_state_label}</Badge>
					{:else if program.joined}
						<Badge variant="outline" class="text-muted-foreground">Joined</Badge>
					{/if}
					<Badge variant={program.offers_bounties ? 'default' : 'secondary'}>
						{program.offers_bounties ? 'Bounty' : 'VDP'}
					</Badge>
					{#if program.submission_state !== SubmissionState.Unknown}
						<Badge variant="outline" class="text-muted-foreground">
							{SUBMISSION_STATE_LABELS[program.submission_state]}
						</Badge>
					{/if}
					{#if payout}
						<Badge variant="outline" class="tabular-nums">{payout}</Badge>
					{/if}
				</Sheet.Title>
				<Sheet.Description class="flex flex-wrap items-center gap-x-3 gap-y-1">
					<a
						href={program.url ?? platformUrl(program.platform)}
						target="_blank"
						rel="noreferrer noopener"
						class="inline-flex items-center gap-1 font-mono text-xs hover:underline"
					>
						@{program.handle}
						<ExternalLinkIcon class="size-3" />
					</a>
					{#if program.reports_for_user}
						<span class="text-xs">{program.reports_for_user} of your reports</span>
					{/if}
					{#if detail?.scopes_synced_at}
						<span class="text-xs">Scope read {formatShortDate(detail.scopes_synced_at)}</span>
					{/if}
					{#if program.requires_2fa}
						<span class="text-xs">2FA required</span>
					{/if}
				</Sheet.Description>
			</Sheet.Header>

			<div class="border-b px-4">
				<CountTabs
					tabs={[
						{ key: 'all', label: 'All scope' },
						{ key: ScopeState.InScope, label: 'In scope' },
						{ key: ScopeState.OutOfScope, label: 'Out of scope' }
					]}
					value={tab}
					counts={counts as Record<string, number>}
					onChange={(k) => (tab = k)}
				/>
			</div>

			<div class="border-b bg-muted/20 px-4 py-2 text-xs text-muted-foreground">
				<span class="font-medium text-foreground">{program.source_label}</span>
				· {SOURCE_NOTES[program.source] ?? ''}
			</div>

			<ScrollArea.Root class="min-h-0 flex-1">
				{#if loading}
					<div class="flex items-center justify-center gap-2 p-10 text-sm text-muted-foreground">
						<Spinner class="size-4" />
						Loading scope
					</div>
				{:else if scopes.length === 0 && detail?.scopes_synced_at}
					<EmptyState
						title="This program publishes no structured scope"
						description={`${program.platform_label} returned no scope assets for it. The scope is described in the program policy instead, so there is nothing reNgine can add as a target from here.`}
						class="p-10"
					>
						<Button
							href={program.url ?? platformUrl(program.platform)}
							target="_blank"
							rel="noreferrer noopener"
							variant="outline"
							size="sm"
						>
							<ExternalLinkIcon class="mr-2 size-3.5" />
							Read the policy on {program.platform_label}
						</Button>
					</EmptyState>
				{:else if scopes.length === 0}
					<EmptyState
						title="Scope not fetched yet"
						description={`reNgine has not read this program's scope from ${program.platform_label}.`}
						class="p-10"
					>
						<LoadingButton loading={syncing} variant="outline" size="sm" onclick={refreshScope}>
							<RefreshCwIcon class="mr-2 size-3.5" />
							Fetch scope
						</LoadingButton>
					</EmptyState>
				{:else}
					{#if tab !== ScopeState.OutOfScope && unreachableTotal > 0}
						<div class="border-b bg-muted/30 px-4 py-2.5 text-xs text-muted-foreground">
							<span class="font-medium text-foreground">{unreachableTotal} assets</span> in this
							program cannot be reached by a scan:
							{unreachableEntries.map(([label, n]) => `${n} ${label}`).join(' · ')}
						</div>
					{/if}
					<div>
						{#each visible as scope (scope.id)}
							<ScopeRow
								{scope}
								selected={selected.has(scope.id)}
								allowOutOfScope={showOutOfScope}
								onToggle={toggle}
							/>
						{/each}
					</div>
				{/if}
			</ScrollArea.Root>

			{#if scopes.length > 0}
				<Sheet.Footer class="gap-3 border-t p-4">
					{#if selectedOutOfScope > 0}
						<div
							class="flex items-start gap-2 rounded-md border border-warning/25 bg-warning/10 p-2.5 text-xs"
						>
							<TriangleAlertIcon class="mt-0.5 size-3.5 shrink-0 text-warning" />
							<span>
								{selectedOutOfScope}
								{selectedOutOfScope === 1 ? 'asset is' : 'assets are'} marked out of scope by the program.
								Scanning them is not authorised by this policy.
							</span>
						</div>
					{/if}

					{#if outOfScopeImportable > 0}
						<label class="flex items-center gap-2 text-xs text-muted-foreground">
							<Switch checked={showOutOfScope} onCheckedChange={setAllowOutOfScope} />
							Allow selecting the {outOfScopeImportable} out-of-scope
							{outOfScopeImportable === 1 ? 'asset' : 'assets'}
						</label>
					{/if}

					<div class="flex w-full items-center justify-between gap-2">
						<div class="flex items-center gap-3 text-xs text-muted-foreground">
							<span class="tabular-nums">{selected.size} selected</span>
							<Button variant="link" size="sm" class="h-auto p-0" onclick={selectAllVisible}>
								Select all shown
							</Button>
						</div>
						<Button
							disabled={selected.size === 0 || !projectId}
							onclick={() => (importOpen = true)}
						>
							Add {selected.size} as {selected.size === 1 ? 'target' : 'targets'}
						</Button>
					</div>
				</Sheet.Footer>
			{/if}
		{/if}
	</Sheet.Content>
</Sheet.Root>

{#if program}
	<ImportDialog
		{program}
		count={selected.size}
		outOfScopeCount={selectedOutOfScope}
		open={importOpen}
		{importing}
		onOpenChange={(v) => (importOpen = v)}
		onConfirm={runImport}
	/>
{/if}
