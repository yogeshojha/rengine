<script lang="ts">
	import { toast } from 'svelte-sonner';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import CopyButton from '$lib/components/copy-button.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
	import {
		SEVERITY_CHIP,
		SEVERITY_LABELS,
		VulnState,
		VULN_STATE_LABELS
	} from '$lib/config/vulnerabilities';
	import { EVIDENCE_LABELS, Evidence } from '$lib/config/evidence';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { epssLabel } from '$lib/config/threat-intel';
	import type { ScanFindings } from '$lib/types/scan';
	import type { VulnerabilityRead } from '$lib/utilities/vulns';
	import { findingsOf, forgetFindings, findingHref, findingsHref } from './findings';
	import { historyPrefs } from './prefs.svelte';

	const LIMIT = 60;
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];

	interface Props {
		projectId: string;
		scanId: string;
		findings: ScanFindings | null | undefined;
		live: boolean;
		onChanged: () => void;
		onHover?: (severity: string | null) => void;
	}

	let { projectId, scanId, findings, live, onChanged, onHover }: Props = $props();

	let shown = $derived(historyPrefs.severities);
	let expected = $derived(
		findings
			? shown.reduce((n, s) => n + ((findings[s as keyof ScanFindings] as number) ?? 0), 0)
			: 0
	);
	let version = $derived(
		findings ? `${findings.critical}.${findings.high}.${findings.medium}` : ''
	);
	let items = $state<VulnerabilityRead[] | null>(null);
	let total = $state(0);
	let failed = $state(false);
	let busy = $state<string | null>(null);
	let attempt = $state(0);
	let seq = 0;

	$effect(() => {
		const sev = shown;
		const v = version;
		void attempt;
		if (!findings?.covered || expected === 0) {
			items = [];
			return;
		}
		const mine = ++seq;
		failed = false;
		findingsOf(projectId, scanId, sev, LIMIT, v)
			.then((r) => {
				if (mine !== seq) return;
				items = r.items;
				total = r.total;
			})
			.catch(() => mine === seq && (failed = true));
	});

	let groups = $derived(
		shown
			.map((sev) => ({ sev, rows: (items ?? []).filter((f) => f.severity === sev) }))
			.filter((g) => g.rows.length)
	);

	async function triage(f: VulnerabilityRead, state: VulnState) {
		busy = f.id;
		try {
			await vulnerabilitiesApi.triage(projectId, scanId, f.fingerprint, state);
			items = (items ?? []).filter((x) => x.fingerprint !== f.fingerprint);
			forgetFindings(scanId);
			onChanged();
			toast.success(`${VULN_STATE_LABELS[state]}: ${f.template_name}`, {
				action: {
					label: 'Undo',
					onClick: async () => {
						try {
							await vulnerabilitiesApi.triage(projectId, scanId, f.fingerprint, VulnState.OPEN);
							forgetFindings(scanId);
							onChanged();
						} catch {
							toast.error('Triage not undone');
						}
					}
				}
			});
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Finding not triaged');
		} finally {
			busy = null;
		}
	}
</script>

<div class="flex items-center justify-between gap-3 border-b px-3 py-1.5">
	<span class="text-2xs text-muted-foreground">
		{historyPrefs.showMedium ? 'Critical, high and medium' : 'Critical and high'}
	</span>
	<label class="flex cursor-pointer items-center gap-1.5 text-xs">
		<Checkbox
			id="brief-medium-{scanId}"
			class="size-3.5"
			checked={historyPrefs.showMedium}
			onCheckedChange={(v) => (historyPrefs.showMedium = v === true)}
		/>
		<span class="size-2 rounded-full bg-sev-medium" aria-hidden="true"></span>
		Show medium
		{#if findings?.covered}
			<span class="font-mono text-muted-foreground tabular-nums">{findings.medium}</span>
		{/if}
	</label>
</div>

{#if !findings?.covered}
	<p class="px-1 py-6 text-sm text-muted-foreground">
		{live ? 'Not run yet' : 'Not scanned'}
	</p>
{:else if expected === 0}
	<div class="flex items-center gap-3 px-1 py-6 text-sm text-muted-foreground">
		<span>No critical or high findings.</span>
		{#if !historyPrefs.showMedium && (findings?.medium ?? 0) > 0}
			<button
				type="button"
				class="text-primary hover:text-primary/80"
				onclick={() => (historyPrefs.showMedium = true)}
			>
				Show {findings?.medium} medium
			</button>
		{/if}
	</div>
{:else if failed}
	<div class="flex items-center gap-3 px-1 py-6 text-sm text-muted-foreground">
		<span>Findings not loaded.</span>
		<button type="button" class="text-primary hover:text-primary/80" onclick={() => attempt++}>
			Retry
		</button>
	</div>
{:else if items === null}
	<div class="space-y-2 py-3">
		{#each { length: Math.min(expected, 4) } as _, i (i)}
			<Skeleton class="h-12" />
		{/each}
	</div>
{:else}
	<div class="flex flex-col">
		{#each groups as g (g.sev)}
			<div
				class="sticky top-0 z-1 flex items-center gap-2 bg-muted/40 px-3 py-1.5 text-2xs font-semibold tracking-wide uppercase backdrop-blur {SEVERITY_CHIP[
					g.sev
				].ink}"
			>
				{SEVERITY_LABELS[g.sev]}
				<span class="font-mono tabular-nums"
					>{(findings?.[g.sev as keyof ScanFindings] as number) ?? g.rows.length}</span
				>
			</div>
			{#each g.rows as f (f.id)}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="group/f relative flex items-start gap-3 border-b border-border/50 py-2.5 pr-2 pl-4 hover:bg-muted/30"
					onmouseenter={() => onHover?.(g.sev)}
					onmouseleave={() => onHover?.(null)}
				>
					<span
						class="absolute inset-y-1.5 left-0 w-[3px] rounded-full {SEVERITY_CHIP[g.sev].edge}"
						aria-hidden="true"
					></span>
					<div class="min-w-0 flex-1">
						<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
							<span class="text-sm font-medium">{f.template_name}</span>
							{#if f.is_new}
								<span class="rounded bg-foreground px-1 text-2xs font-semibold text-background"
									>New</span
								>
							{/if}
							{#if f.evidence === Evidence.PROVEN}
								<span
									class="rounded px-1 text-2xs font-semibold ring-1 ring-foreground/40 ring-inset"
									>{EVIDENCE_LABELS[Evidence.PROVEN]}</span
								>
							{/if}
							{#if f.epss_score != null}
								<span
									class="rounded border border-border px-1 font-mono text-2xs text-muted-foreground"
								>
									EPSS {epssLabel(f.epss_score)}
								</span>
							{/if}
						</div>
						<div class="mt-0.5 flex min-w-0 items-center gap-1">
							<span class="truncate font-mono text-xs text-muted-foreground">{f.matched_at}</span>
							<CopyButton
								value={f.matched_at}
								class="shrink-0 opacity-0 group-hover/f:opacity-100 focus-visible:opacity-100"
							/>
						</div>
						{#if f.replays > 0}
							<div class="mt-0.5 text-2xs text-muted-foreground">
								Confirmed on {f.replays} equivalent {f.replays === 1 ? WEB.noun : WEB.nounPlural}
							</div>
						{/if}
					</div>
					<div class="flex shrink-0 items-center gap-1">
						<Button
							variant="ghost"
							size="sm"
							class="h-7 px-2 text-xs"
							disabled={busy === f.id}
							onclick={() => triage(f, VulnState.FALSE_POSITIVE)}
						>
							False positive
						</Button>
						<Button
							variant="ghost"
							size="sm"
							class="h-7 px-2 text-xs"
							disabled={busy === f.id}
							onclick={() => triage(f, VulnState.ACCEPTED)}
						>
							Accept risk
						</Button>
						<Button
							variant="ghost"
							size="sm"
							class="h-7 gap-1 px-2 text-xs"
							href={findingHref(scanId, f.id)}
						>
							Open <ExternalLink class="size-3" />
						</Button>
					</div>
				</div>
			{/each}
		{/each}
		{#if total > (items?.length ?? 0)}
			<a
				href={findingsHref(scanId, shown)}
				class="px-4 py-2 text-xs text-primary hover:text-primary/80"
			>
				Open all {total} in results
			</a>
		{/if}
	</div>
{/if}
