<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import Search from '@lucide/svelte/icons/search';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import * as Alert from '$lib/components/ui/alert';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import AskTrace from '../ask/ask-trace.svelte';
	import { investigateApi } from '$lib/api/investigate';
	import { LONG_REQUEST_TIMEOUT_MS } from '$lib/api/client';
	import { ROUTES } from '$lib/config/routes';
	import {
		PlanResult,
		PlanState,
		StreamEvent,
		Verdict,
		type VerdictValue
	} from '$lib/config/investigate';
	import { relativeTime } from '$lib/utilities/dates';
	import type { AskTraceStep } from '$lib/types/ask';
	import type { InvestigateBrief, Investigation } from '$lib/types/investigate';

	interface Props {
		projectId: string;
		scanId: string;
		fingerprint: string;
	}

	let { projectId, scanId, fingerprint }: Props = $props();

	const NO_ANSWER = 'The verdict did not arrive. Check the api log.';

	let brief = $state<InvestigateBrief | null>(null);
	let loading = $state(false);
	let investigation = $state<Investigation | null>(null);
	let running = $state(false);
	let draft = $state<{ text: string; trace: AskTraceStep[] } | null>(null);
	let error = $state('');
	const busyPlans = new SvelteSet<string>();
	let loadedFor = '';
	let generation = 0;
	let controller: AbortController | null = null;
	let timer: ReturnType<typeof setTimeout> | null = null;

	let key = $derived(`${projectId}:${scanId}:${fingerprint}`);
	let available = $derived(brief?.available ?? false);
	let proposed = $derived(investigation?.plans.filter((p) => p.state === PlanState.PROPOSED) ?? []);
	let settledPlans = $derived(
		investigation?.plans.filter((p) => p.state !== PlanState.PROPOSED) ?? []
	);
	let proposedRequests = $derived(proposed.reduce((sum, p) => sum + (p.request_count ?? 1), 0));

	const VERDICT_VARIANT: Record<string, 'success' | 'warning' | 'secondary' | 'outline'> = {
		[Verdict.REPRODUCED]: 'success',
		[Verdict.CONFIRMED]: 'success',
		[Verdict.NOT_REPRODUCED]: 'secondary',
		[Verdict.FALSE_POSITIVE]: 'secondary',
		[Verdict.NEEDS_PERSON]: 'warning',
		[Verdict.PENDING]: 'outline'
	};

	$effect(() => {
		if (loadedFor === key) return;
		loadedFor = key;
		untrack(() => void load());
	});

	$effect(() => () => cancel());

	function verdictVariant(
		v: VerdictValue | string
	): 'success' | 'warning' | 'secondary' | 'outline' {
		return VERDICT_VARIANT[v] ?? 'outline';
	}

	function cancel() {
		generation += 1;
		controller?.abort();
		controller = null;
		if (timer) clearTimeout(timer);
		timer = null;
		running = false;
		draft = null;
	}

	async function load() {
		cancel();
		const mine = ++generation;
		loading = true;
		error = '';
		try {
			const found = await investigateApi.brief(projectId, scanId, fingerprint);
			if (mine !== generation) return;
			brief = found;
			investigation = found.investigation;
		} catch (e) {
			if (mine === generation) error = (e as Error).message;
		} finally {
			if (mine === generation) loading = false;
		}
	}

	async function run() {
		if (running || !available) return;
		const mine = ++generation;
		running = true;
		draft = { text: '', trace: [] };
		error = '';
		let settled = false;
		controller = new AbortController();
		const own = controller;
		timer = setTimeout(() => own.abort(), LONG_REQUEST_TIMEOUT_MS);
		try {
			await investigateApi.run(
				projectId,
				{ scan_id: scanId, fingerprint },
				(frame) => {
					if (mine !== generation) return;
					if (frame.event === StreamEvent.DONE || frame.event === StreamEvent.ERROR) settled = true;
					onFrame(frame);
				},
				own.signal
			);
			if (mine === generation && !settled) error = NO_ANSWER;
		} catch (e) {
			if (mine === generation) error = (e as Error).message;
		} finally {
			if (mine === generation) {
				if (timer) clearTimeout(timer);
				timer = null;
				controller = null;
				running = false;
				draft = null;
			}
		}
	}

	function onFrame(frame: Parameters<Parameters<typeof investigateApi.run>[2]>[0]) {
		if (frame.event === StreamEvent.TRACE) {
			if (!draft) return;
			const { index, ...step } = frame.data;
			const trace = [...draft.trace];
			trace[index] = step;
			draft = { ...draft, trace };
		} else if (frame.event === StreamEvent.DELTA) {
			if (!draft) return;
			draft = { ...draft, text: draft.text + frame.data.text };
		} else if (frame.event === StreamEvent.DONE) {
			investigation = frame.data;
		} else if (frame.event === StreamEvent.ERROR) {
			error = frame.data.message;
		}
	}

	async function decide(action: 'approve' | 'decline', ids: string[]) {
		if (!ids.length) return;
		ids.forEach((id) => busyPlans.add(id));
		try {
			investigation =
				action === 'approve'
					? await investigateApi.approve(projectId, ids)
					: await investigateApi.decline(projectId, ids);
			toast.success(action === 'approve' ? 'Approved. The check runs now.' : 'Declined');
		} catch (e) {
			toast.error((e as Error).message);
		} finally {
			ids.forEach((id) => busyPlans.delete(id));
		}
	}

	function resultVariant(result: string | null): 'success' | 'secondary' {
		return result === PlanResult.REPRODUCED ? 'success' : 'secondary';
	}
</script>

<div class="flex flex-col gap-5 p-5">
	{#if loading && !investigation}
		<div class="flex flex-col gap-3">
			<Skeleton class="h-6 w-40" />
			<Skeleton class="h-4 w-full" />
			<Skeleton class="h-4 w-4/5" />
		</div>
	{:else}
		{#if brief && !available}
			<Alert.Root>
				<Alert.Title>{brief.off_reason}</Alert.Title>
				<Alert.Description>
					<a href={ROUTES.ai('connection')} class="font-medium text-primary">Open AI settings</a>
				</Alert.Description>
			</Alert.Root>
		{/if}

		{#if investigation}
			<div class="flex flex-wrap items-center gap-2">
				<Badge variant={verdictVariant(investigation.verdict)} class="gap-1">
					{#if investigation.verified}
						<ShieldCheck />
					{/if}
					{investigation.verdict_label}
				</Badge>
				{#if investigation.verified && investigation.verified_at}
					<span class="text-2xs text-muted-foreground">
						Verified {relativeTime(investigation.verified_at)}
					</span>
				{/if}
				{#if investigation.by_rule}
					<span class="text-2xs text-muted-foreground">Started by a rule</span>
				{/if}
			</div>

			{#if investigation.rationale}
				<p class="m-0 text-sm leading-relaxed whitespace-pre-wrap wrap-anywhere">
					{investigation.rationale}
				</p>
			{/if}
		{/if}

		{#if running}
			<div class="flex flex-col gap-3">
				{#if draft?.trace.length}
					<AskTrace steps={draft.trace} live />
				{/if}
				{#if draft?.text}
					<p class="m-0 text-sm leading-relaxed whitespace-pre-wrap wrap-anywhere">{draft.text}</p>
				{:else}
					<div class="flex flex-col gap-2">
						<Skeleton class="h-4 w-full" />
						<Skeleton class="h-4 w-3/5" />
					</div>
				{/if}
			</div>
		{/if}

		{#if proposed.length}
			<div class="flex flex-col gap-2 rounded-lg border bg-muted/20 p-3">
				<div class="flex items-center justify-between gap-2">
					<span class="text-2xs tracking-wide text-muted-foreground uppercase">
						Proposed · {proposedRequests}
						{proposedRequests === 1 ? 'request' : 'requests'}
					</span>
					<div class="flex items-center gap-1.5">
						<Button
							size="sm"
							variant="outline"
							class="h-7 text-xs"
							disabled={busyPlans.size > 0}
							onclick={() =>
								void decide(
									'decline',
									proposed.map((p) => p.id)
								)}
						>
							Decline all
						</Button>
						<Button
							size="sm"
							class="h-7 text-xs"
							disabled={busyPlans.size > 0}
							onclick={() =>
								void decide(
									'approve',
									proposed.map((p) => p.id)
								)}
						>
							Approve {proposed.length}
						</Button>
					</div>
				</div>
				{#each proposed as plan (plan.id)}
					<div
						class="flex items-start justify-between gap-3 border-t pt-2 first:border-t-0 first:pt-0"
					>
						<div class="flex min-w-0 flex-col gap-0.5">
							<span class="truncate font-mono text-xs"
								>{plan.template_name ?? plan.template_id}</span
							>
							<span class="truncate text-2xs text-muted-foreground">{plan.host}</span>
							{#if plan.reason}
								<span class="text-xs text-muted-foreground">{plan.reason}</span>
							{/if}
						</div>
						<div class="flex shrink-0 items-center gap-1">
							<Button
								size="sm"
								variant="ghost"
								class="h-7 text-xs text-muted-foreground"
								disabled={busyPlans.has(plan.id)}
								onclick={() => void decide('decline', [plan.id])}
							>
								Decline
							</Button>
							<Button
								size="sm"
								class="h-7 text-xs"
								disabled={busyPlans.has(plan.id)}
								onclick={() => void decide('approve', [plan.id])}
							>
								Approve
							</Button>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		{#if settledPlans.length}
			<div class="flex flex-col gap-2">
				{#each settledPlans as plan (plan.id)}
					<div class="flex items-center justify-between gap-3 text-xs">
						<div class="flex min-w-0 flex-col gap-0.5">
							<span
								class="truncate font-mono {plan.state === PlanState.REFUSED
									? 'text-muted-foreground line-through'
									: ''}"
							>
								{plan.template_name ?? plan.template_id}
							</span>
							<span class="truncate text-2xs text-muted-foreground">{plan.host}</span>
						</div>
						{#if plan.state === PlanState.REFUSED && plan.refusal_label}
							<Badge variant="outline" class="shrink-0 text-muted-foreground">
								{plan.refusal_label}
							</Badge>
						{:else if plan.result}
							<Badge variant={resultVariant(plan.result)} class="shrink-0">
								{plan.result_label}
							</Badge>
						{:else}
							<span class="shrink-0 text-2xs text-muted-foreground">{plan.state_label}</span>
						{/if}
					</div>
				{/each}
			</div>
		{/if}

		{#if error}
			<Alert.Root variant="destructive">
				<Alert.Title>No verdict</Alert.Title>
				<Alert.Description>{error}</Alert.Description>
			</Alert.Root>
		{/if}

		{#if available && !running}
			<div class="flex items-center gap-2">
				<Button
					variant={investigation ? 'outline' : 'default'}
					size="sm"
					onclick={() => void run()}
				>
					<Search />
					{investigation ? 'Investigate again' : 'Investigate'}
				</Button>
				{#if !investigation}
					<span class="text-xs text-muted-foreground">No verdict yet.</span>
				{/if}
			</div>
		{/if}
	{/if}
</div>
