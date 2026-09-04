<script lang="ts">
	import { untrack } from 'svelte';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Switch } from '$lib/components/ui/switch';
	import Hint from '$lib/components/hint.svelte';
	import SeverityBar from './results/vulnerabilities/severity-bar.svelte';
	import { vulnTemplatesApi } from '$lib/api/vulnerabilities';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import {
		SEVERITY_HELP,
		SEVERITY_LABELS,
		SEVERITY_ORDER,
		SEVERITY_FILL,
		TEMPLATE_SET_ICONS,
		VULN_STAGE
	} from '$lib/config/vulnerabilities';
	import type { SelectionPreview, TemplateLibraryStats } from '$lib/types/vuln-template';
	import type { StageConfig } from '$lib/types/scan-engine';

	interface Plan {
		enabled: boolean;
		severities: string[];
		template_sets: string[];
	}

	interface Props {
		engineStages: Record<string, StageConfig> | null;
		onChange: (overrides: Record<string, Record<string, unknown>>) => void;
	}

	let { engineStages, onChange }: Props = $props();

	let stats = $state<TemplateLibraryStats | null>(null);
	let statsLoading = $state(true);
	let preview = $state<SelectionPreview | null>(null);
	let previewLoading = $state(false);
	let open = $state(false);
	let plan = $state<Plan | null>(null);
	let previewSeq = 0;
	let debounce: ReturnType<typeof setTimeout>;

	let catalogEntry = $derived(engineCatalogStore.stage(VULN_STAGE));

	// what the engine ships with: its stored values on top of the stage defaults
	let baseline = $derived.by<Plan | null>(() => {
		if (!catalogEntry) return null;
		const stored = (engineStages?.[VULN_STAGE] ?? {}) as Record<string, unknown>;
		const merged = { ...catalogEntry.defaults, ...stored } as Record<string, unknown>;
		return {
			enabled: Boolean(merged.enabled),
			severities: [...((merged.severities as string[]) ?? [])],
			template_sets: [...((merged.template_sets as string[]) ?? [])]
		};
	});

	// fields the launch modal does not edit but the resolved count must still honour
	let carried = $derived.by(() => {
		if (!catalogEntry) return null;
		const stored = (engineStages?.[VULN_STAGE] ?? {}) as Record<string, unknown>;
		const merged = { ...catalogEntry.defaults, ...stored } as Record<string, unknown>;
		return {
			custom_templates: [...((merged.custom_templates as string[]) ?? [])],
			include_tags: [...((merged.include_tags as string[]) ?? [])],
			exclude_tags: [...((merged.exclude_tags as string[]) ?? [])],
			exclude_templates: [...((merged.exclude_templates as string[]) ?? [])],
			headless: Boolean(merged.headless)
		};
	});

	let current = $derived(plan ?? baseline);
	let dirty = $derived.by(() => {
		if (!plan || !baseline) return false;
		return (
			plan.enabled !== baseline.enabled ||
			plan.severities.join() !== baseline.severities.join() ||
			plan.template_sets.join() !== baseline.template_sets.join()
		);
	});
	let sets = $derived(stats?.sets ?? []);
	let ready = $derived(stats?.ready ?? false);

	$effect(() => {
		if (!engineCatalogStore.hasFetched) engineCatalogStore.fetch();
		untrack(() => {
			vulnTemplatesApi
				.stats()
				.then((res) => (stats = res))
				.catch(() => (stats = null))
				.finally(() => (statsLoading = false));
		});
	});

	// a new engine replaces the plan; an edit keeps it
	let baselineKey = $derived(baseline ? JSON.stringify([baseline, carried]) : '');
	let lastBaseline = '';
	$effect(() => {
		const key = baselineKey;
		if (!key || key === lastBaseline) return;
		lastBaseline = key;
		untrack(() => {
			plan = null;
			onChange({});
		});
	});

	function patch(update: Partial<Plan>) {
		const base = current;
		if (!base) return;
		const next = { ...base, ...update };
		plan = next;
		emit(next);
	}

	function emit(next: Plan) {
		if (!baseline) return;
		const overrides: Record<string, unknown> = {};
		if (next.enabled !== baseline.enabled) overrides.enabled = next.enabled;
		if (next.severities.join() !== baseline.severities.join())
			overrides.severities = next.severities;
		if (next.template_sets.join() !== baseline.template_sets.join())
			overrides.template_sets = next.template_sets;
		onChange(Object.keys(overrides).length ? { [VULN_STAGE]: overrides } : {});
	}

	function reset() {
		plan = null;
		onChange({});
	}

	function toggleSeverity(value: string) {
		const base = current;
		if (!base) return;
		patch({
			severities: base.severities.includes(value)
				? base.severities.filter((s) => s !== value)
				: [...base.severities, value].sort(
						(a, b) => SEVERITY_ORDER.indexOf(a) - SEVERITY_ORDER.indexOf(b)
					)
		});
	}

	function toggleSet(key: string) {
		const base = current;
		if (!base) return;
		patch({
			template_sets: base.template_sets.includes(key)
				? base.template_sets.filter((s) => s !== key)
				: [...base.template_sets, key]
		});
	}

	// the count is a promise: it is resolved against the same library the scan will run
	$effect(() => {
		const base = current;
		const isReady = ready;
		clearTimeout(debounce);
		if (!base || !base.enabled || !isReady) {
			preview = null;
			previewLoading = false;
			return;
		}
		const selection = {
			severities: [...base.severities],
			template_sets: [...base.template_sets],
			...(carried ?? {
				custom_templates: [],
				include_tags: [],
				exclude_tags: [],
				exclude_templates: [],
				headless: false
			})
		};
		previewLoading = true;
		const seq = ++previewSeq;
		debounce = setTimeout(() => {
			vulnTemplatesApi
				.selection(selection)
				.then((res) => {
					if (seq === previewSeq) preview = res;
				})
				.catch(() => {
					if (seq === previewSeq) preview = null;
				})
				.finally(() => {
					if (seq === previewSeq) previewLoading = false;
				});
		}, 250);
		return () => clearTimeout(debounce);
	});

	let severityCounts = $derived(
		(preview?.by_severity ?? []).map((s) => ({
			severity: s.key,
			label: s.label,
			count: s.count
		}))
	);
</script>

{#if catalogEntry}
	<div class="space-y-2">
		<div class="flex min-h-9 flex-wrap items-center justify-between gap-x-2 gap-y-1">
			<Label class="flex shrink-0 items-center gap-1.5" for="vuln-plan-switch">
				<ShieldAlert class="size-3.5 text-muted-foreground" />
				Vulnerability scan
				{#if dirty}
					<Badge variant="info" class="text-[10px] font-normal">This run only</Badge>
				{/if}
			</Label>
			<div class="ml-auto flex shrink-0 items-center gap-2">
				<Switch
					id="vuln-plan-switch"
					checked={current?.enabled ?? false}
					disabled={!ready && !current?.enabled}
					onCheckedChange={(value) => patch({ enabled: value })}
					aria-label="Run a vulnerability scan on this run"
				/>
			</div>
		</div>

		{#if statsLoading}
			<Skeleton class="h-9 w-full rounded-md" />
		{:else if !ready}
			<div
				class="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/5 px-3 py-2 text-xs"
			>
				<TriangleAlert class="mt-0.5 size-3.5 shrink-0 text-warning" />
				<p class="text-muted-foreground">
					The check library is empty. Sync it in the Tools Arsenal before a vulnerability scan can
					run.
				</p>
			</div>
		{:else if !current?.enabled}
			<p class="text-[11px] text-muted-foreground">
				Off for this run. Turn it on to test everything this scan finds against
				{stats?.total.toLocaleString()} checks.
			</p>
		{:else}
			<div class="space-y-3 rounded-md border bg-muted/20 p-3">
				<div class="flex flex-wrap items-baseline gap-x-2 gap-y-1">
					{#if previewLoading && !preview}
						<Skeleton class="h-6 w-40" />
					{:else if preview}
						<span class="text-lg leading-6 font-semibold tabular-nums">
							{preview.total.toLocaleString()}
						</span>
						<span class="text-xs text-muted-foreground">
							checks will run against every asset this scan finds
						</span>
					{/if}
					{#if dirty}
						<Hint text="Return to what this engine runs by default">
							{#snippet child(props)}
								<Button
									{...props}
									variant="ghost"
									size="sm"
									class="ml-auto h-6 gap-1 px-1.5 text-xs text-muted-foreground"
									onclick={reset}
								>
									<RotateCcw class="size-3" /> Reset
								</Button>
							{/snippet}
						</Hint>
					{/if}
				</div>

				{#if preview && preview.total > 0}
					<SeverityBar counts={severityCounts} height="h-1.5" />
					<div class="flex flex-wrap gap-x-3 gap-y-1">
						{#each severityCounts as part (part.severity)}
							<span class="flex items-center gap-1 text-[11px] text-muted-foreground">
								<span
									class="size-1.5 rounded-full"
									style="background:{SEVERITY_FILL[part.severity]}"
								></span>
								{part.label}
								<span class="font-medium text-foreground tabular-nums">
									{part.count.toLocaleString()}
								</span>
							</span>
						{/each}
					</div>
				{/if}
				{#each preview?.warnings ?? [] as warning (warning)}
					<p class="text-[11px] text-warning">{warning}</p>
				{/each}

				<Collapsible.Root bind:open>
					<Collapsible.Trigger
						class="flex w-full items-center justify-between rounded-sm text-xs text-muted-foreground hover:text-foreground"
					>
						<span>Severity and check sets</span>
						<ChevronDown class="size-3.5 transition-transform {open ? 'rotate-180' : ''}" />
					</Collapsible.Trigger>
					<Collapsible.Content class="space-y-3 pt-3">
						<div class="space-y-1.5">
							<p class="text-[11px] font-medium text-muted-foreground">Severity</p>
							<div class="flex flex-wrap gap-1.5">
								{#each SEVERITY_ORDER as value (value)}
									{@const on = current?.severities.includes(value) ?? false}
									<Hint text={SEVERITY_HELP[value]}>
										{#snippet child(props)}
											<button
												{...props}
												type="button"
												class="flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors {on
													? 'border-primary/40 bg-primary/5'
													: 'border-border text-muted-foreground hover:bg-accent'}"
												aria-pressed={on}
												onclick={() => toggleSeverity(value)}
											>
												<span
													class="size-2 rounded-full {on ? '' : 'opacity-40'}"
													style="background:{SEVERITY_FILL[value]}"
												></span>
												{SEVERITY_LABELS[value]}
											</button>
										{/snippet}
									</Hint>
								{/each}
							</div>
						</div>

						<div class="space-y-1.5">
							<p class="text-[11px] font-medium text-muted-foreground">Check sets</p>
							<div class="grid grid-cols-1 gap-1">
								{#each sets as set (set.key)}
									{@const on = current?.template_sets.includes(set.key) ?? false}
									{@const Icon = TEMPLATE_SET_ICONS[set.key]}
									<Hint text={set.description}>
										{#snippet child(props)}
											<button
												{...props}
												type="button"
												class="flex items-center gap-2 rounded-md border px-2 py-1.5 text-left text-xs transition-colors {on
													? 'border-primary/40 bg-primary/5'
													: 'border-border text-muted-foreground hover:bg-accent'}"
												aria-pressed={on}
												onclick={() => toggleSet(set.key)}
											>
												{#if Icon}
													<Icon class="size-3.5 shrink-0 {on ? '' : 'opacity-60'}" />
												{/if}
												<span class="min-w-0 flex-1 truncate">{set.label}</span>
												<span class="shrink-0 tabular-nums opacity-60">
													{set.count.toLocaleString()}
												</span>
											</button>
										{/snippet}
									</Hint>
								{/each}
							</div>
						</div>
					</Collapsible.Content>
				</Collapsible.Root>
			</div>
		{/if}
	</div>
{/if}
