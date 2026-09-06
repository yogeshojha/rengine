<script lang="ts">
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import SectionHead from '../section-head.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { TargetType, type Target } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import type { ScanRead } from '$lib/types/scan';
	import type { TargetSummaryRead } from '$lib/types/target-summary';
	import type { LiveRun } from '$lib/stores/live-scans.svelte';
	import {
		durationText,
		elapsedSeconds,
		formatSeconds,
		isLiveStatus,
		SCAN_STATUS_DOT,
		SCAN_STATUS_LABEL,
		SCAN_STATUS_PILL
	} from '$lib/utilities/scan-status';

	interface Props {
		target: Target;
		creator: string | null;
		summary: TargetSummaryRead | null;
		history: ScanRead[];
		loaded: boolean;
		run: LiveRun | undefined;
		now: number;
	}

	let { target, creator, summary, history, loaded, run, now }: Props = $props();

	const SHOWN = 6;
	const COUNTS: { key: keyof ScanRead; spec: (typeof SURFACE)[SurfaceDimension] }[] = [
		{ key: 'subdomains_found', spec: SURFACE[SurfaceDimension.WEB_ASSETS] },
		{ key: 'endpoints_found', spec: SURFACE[SurfaceDimension.ENDPOINTS] },
		{ key: 'open_ports_found', spec: SURFACE[SurfaceDimension.SERVICES] },
		{ key: 'ips_found', spec: SURFACE[SurfaceDimension.IPS] },
		{ key: 'vulnerabilities_found', spec: SURFACE[SurfaceDimension.VULNERABILITIES] }
	];
	const fmtTime = (iso: string) =>
		new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
	const fmtDay = (iso: string) => {
		const d = new Date(iso);
		const today = new Date();
		if (d.toDateString() === today.toDateString()) return 'Today';
		return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	};

	const started = (s: ScanRead) => new Date(s.started_at ?? s.created_at).getTime();

	// focused rescans hang off the run that seeded them, never on the rail of their own
	let runs = $derived.by(() => {
		const sorted = [...history].sort((a, b) => started(b) - started(a));
		const census = sorted.filter((s) => s.scope !== 'focused').slice(0, SHOWN);
		const shown = new Set(census.map((s) => s.id));
		const children = new Map<string, ScanRead[]>();
		for (const s of sorted) {
			if (s.scope !== 'focused' || !s.parent_scan_id || !shown.has(s.parent_scan_id)) continue;
			const bucket = children.get(s.parent_scan_id);
			if (bucket) bucket.push(s);
			else children.set(s.parent_scan_id, [s]);
		}
		return census.map((scan) => ({ scan, rescans: (children.get(scan.id) ?? []).slice(0, 4) }));
	});
	let total = $derived(summary?.scans_total ?? history.length);

	function detailFor(s: ScanRead): string {
		const live = isLiveStatus(s.status);
		if (live) {
			const parts: string[] = [];
			if (run?.stage?.title) parts.push(run.stage.title);
			const e = elapsedSeconds(s, now);
			if (e != null) parts.push(formatSeconds(e));
			return parts.join(' · ');
		}
		const took = s.duration_seconds != null ? durationText(s.duration_seconds) : null;
		if (s.status === 'cancelled') return took ? `stopped after ${took}` : 'stopped';
		if (s.status === 'failed') return s.error ? s.error : 'failed';
		const parts: string[] = [];
		if (took) parts.push(took);
		if (s.is_first_scan) parts.push('baseline, later runs compare against it');
		else if (s.new_subdomains === 0 && s.gone_subdomains === 0) parts.push('no change');
		return parts.join(' · ');
	}
	let latestId = $derived(summary?.latest_scan?.id ?? null);
	let observed = $derived(
		new Map((summary?.surface ?? []).filter((m) => m.covered).map((m) => [m.key, m.value ?? 0]))
	);
	function countsFor(s: ScanRead): { text: string; up?: boolean }[] {
		const out: { text: string; up?: boolean }[] = [];
		for (const c of COUNTS) {
			const n =
				s.id === latestId && observed.has(c.spec.key)
					? observed.get(c.spec.key)!
					: Number(s[c.key] ?? 0);
			if (!n) continue;
			const isWeb = c.key === 'subdomains_found';
			if (isWeb && s.status === 'completed' && (s.new_subdomains ?? 0) > 0)
				out.push({ text: `+${s.new_subdomains!.toLocaleString()} ${c.spec.nounPlural}`, up: true });
			else out.push({ text: `${n.toLocaleString()} ${n === 1 ? c.spec.noun : c.spec.nounPlural}` });
		}
		return out;
	}
	let enrichment = $derived.by(() => {
		const parts: string[] = [];
		const t = target.target_type;
		const state = (st: TaskStatus) =>
			st === TaskStatus.FAILED ? 'failed' : st === TaskStatus.SUCCESS ? 'enriched' : 'pending';
		if (t === TargetType.DOMAIN || t === TargetType.URL)
			parts.push(`DNS ${state(target.dns_status)}`);
		parts.push(`WHOIS ${state(target.whois_status)}`);
		if (t === TargetType.IP || t === TargetType.IP_RANGE || t === TargetType.ASN)
			parts.push(`BGP ${state(target.bgp_status)}`);
		return parts.join(' · ');
	});
</script>

<section class="flex flex-col gap-3 border-t py-5">
	<SectionHead
		title="Activity"
		count={total ? `${total.toLocaleString()} ${total === 1 ? 'run' : 'runs'}` : null}
	>
		{#if total > runs.length}
			<a
				href={ROUTES.scansForTarget(target.id)}
				class="flex items-center gap-1 font-medium text-primary"
			>
				All runs <ArrowRight class="size-3" />
			</a>
		{/if}
	</SectionHead>

	{#if !loaded}
		<div class="flex flex-col gap-3">
			{#each Array(2) as _, i (i)}
				<Skeleton class="h-12 w-full" />
			{/each}
		</div>
	{:else}
		<ol class="flex flex-col">
			{#each runs as { scan: s, rescans } (s.id)}
				{@const started = s.started_at ?? s.created_at}
				{@const counts = countsFor(s)}
				<li class="grid grid-cols-[5.5rem_1.25rem_minmax(0,1fr)] gap-x-2.5">
					<span class="pt-0.5 text-right text-xs leading-tight text-muted-foreground">
						<span class="block font-medium text-foreground">{fmtDay(started)}</span>
						{fmtTime(started)}
					</span>
					<span class="relative flex justify-center">
						<span class="z-[1] flex h-5 items-center"
							><span
								class="size-2.5 rounded-full border-2 {SCAN_STATUS_DOT[s.status]}"
								aria-hidden="true"
							></span></span
						>
						<span
							class="absolute top-[17px] -bottom-1 left-1/2 border-l-2 border-dotted"
							aria-hidden="true"
						></span>
					</span>
					<span class="flex min-w-0 flex-col gap-1.5 pb-[18px]">
						<span class="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px]">
							<a href={ROUTES.scan(s.id)} class="font-semibold hover:underline">{s.engine_name}</a>
							<span
								class="rounded-full px-[7px] text-[11px] font-semibold tracking-[0.02em] {SCAN_STATUS_PILL[
									s.status
								]}"
							>
								{SCAN_STATUS_LABEL[s.status]}
							</span>
							<span class="text-muted-foreground">{detailFor(s)}</span>
						</span>
						{#if counts.length}
							<span class="flex flex-wrap gap-1.5">
								{#each counts as c (c.text)}
									<span
										class="rounded-md border px-[7px] py-px text-xs tabular-nums {c.up
											? 'border-success/40 text-success'
											: 'text-muted-foreground'}"
									>
										{c.text}
									</span>
								{/each}
							</span>
						{/if}
					</span>
				</li>
				{#each rescans as r (r.id)}
					<li class="grid grid-cols-[5.5rem_1.25rem_1.25rem_minmax(0,1fr)] gap-x-2.5">
						<span class="pt-0.5 text-right text-xs leading-tight text-muted-foreground">
							{fmtTime(r.started_at ?? r.created_at)}
						</span>
						<span class="relative flex justify-center">
							<span class="absolute -top-1 -bottom-1 left-1/2 border-l-2 border-dotted"></span>
						</span>
						<span class="relative flex justify-center">
							<span
								class="absolute top-[9px] -left-[calc(1.25rem-1px)] w-[calc(0.625rem+1px)] border-t-2 border-dotted"
								aria-hidden="true"
							></span>
							<span class="z-[1] flex h-5 items-center">
								<span
									class="size-2 rounded-full border-2 border-primary bg-background"
									aria-hidden="true"
								></span>
							</span>
						</span>
						<span class="flex min-w-0 flex-col gap-1 pb-3.5">
							<span class="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px]">
								<a href={ROUTES.scan(r.id)} class="font-medium hover:underline">{r.engine_name}</a>
								<span
									class="rounded-full px-[7px] text-[11px] font-semibold tracking-[0.02em] {SCAN_STATUS_PILL[
										r.status
									]}"
								>
									{SCAN_STATUS_LABEL[r.status]}
								</span>
								<span class="text-muted-foreground">{detailFor(r)}</span>
							</span>
						</span>
					</li>
				{/each}
			{/each}
			<li class="grid grid-cols-[5.5rem_1.25rem_minmax(0,1fr)] gap-x-2.5">
				<span class="pt-0.5 text-right text-xs leading-tight text-muted-foreground">
					<span class="block font-medium text-foreground">{fmtDay(target.created_at)}</span>
					{fmtTime(target.created_at)}
				</span>
				<span class="relative flex justify-center">
					<span class="z-[1] flex h-5 items-center"
						><span
							class="size-2.5 rounded-full border-2 border-muted-foreground/60 bg-card"
							aria-hidden="true"
						></span></span
					>
				</span>
				<span class="pb-1 text-[13px] text-muted-foreground">
					Target added{creator ? ` by ${creator}` : ''} · {enrichment}
				</span>
			</li>
		</ol>
	{/if}
</section>
