<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import SeverityBar from './results/vulnerabilities/severity-bar.svelte';
	import { vulnTemplatesApi } from '$lib/api/vulnerabilities';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import {
		SEVERITY_HELP,
		SEVERITY_LABELS,
		SEVERITY_ORDER,
		SEVERITY_FILL,
		severityRank,
		TEMPLATE_SET_ICONS,
		VULN_STAGE
	} from '$lib/config/vulnerabilities';
	import type { SelectionPreview, TemplateLibraryStats } from '$lib/types/vuln-template';
	import type { StageConfig } from '$lib/types/scan-engine';

	interface Props {
		config: StageConfig | undefined;
		onField: (field: string, value: unknown) => void;
	}

	let { config, onField }: Props = $props();

	let stats = $state<TemplateLibraryStats | null>(null);
	let statsLoading = $state(true);
	let preview = $state<SelectionPreview | null>(null);
	let previewLoading = $state(false);
	let open = $state(false);
	let previewSeq = 0;
	let debounce: ReturnType<typeof setTimeout>;

	let catalogEntry = $derived(engineCatalogStore.stage(VULN_STAGE));

	let merged = $derived(
		catalogEntry ? ({ ...catalogEntry.defaults, ...config } as Record<string, unknown>) : null
	);

	let current = $derived(
		merged
			? {
					severities: [...((merged.severities as string[]) ?? [])],
					template_sets: [...((merged.template_sets as string[]) ?? [])]
				}
			: null
	);

	let carried = $derived(
		merged
			? {
					custom_templates: [...((merged.custom_templates as string[]) ?? [])],
					include_tags: [...((merged.include_tags as string[]) ?? [])],
					exclude_tags: [...((merged.exclude_tags as string[]) ?? [])],
					exclude_templates: [...((merged.exclude_templates as string[]) ?? [])],
					headless: Boolean(merged.headless)
				}
			: null
	);

	let sets = $derived(stats?.sets ?? []);
	let ready = $derived(stats?.ready ?? false);

	$effect(() => {
		if (!engineCatalogStore.hasFetched) engineCatalogStore.fetch();
	});

	$effect(() => {
		vulnTemplatesApi
			.stats()
			.then((res) => (stats = res))
			.catch(() => (stats = null))
			.finally(() => (statsLoading = false));
	});

	function toggleSeverity(value: string) {
		const base = current;
		if (!base) return;
		onField(
			'severities',
			base.severities.includes(value)
				? base.severities.filter((s) => s !== value)
				: [...base.severities, value].sort((a, b) => severityRank(a) - severityRank(b))
		);
	}

	function toggleSet(key: string) {
		const base = current;
		if (!base) return;
		onField(
			'template_sets',
			base.template_sets.includes(key)
				? base.template_sets.filter((s) => s !== key)
				: [...base.template_sets, key]
		);
	}

	$effect(() => {
		const base = current;
		const isReady = ready;
		clearTimeout(debounce);
		if (!base || !isReady) {
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
		{#if statsLoading}
			<Skeleton class="h-9 w-full rounded-md" />
		{:else if !ready}
			<div
				class="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/5 px-3 py-2 text-xs"
			>
				<TriangleAlert class="mt-0.5 size-3.5 shrink-0 text-warning" />
				<p class="text-muted-foreground">The check library is empty. Sync it in Arsenal.</p>
			</div>
		{:else}
			<div class="space-y-3 rounded-md border bg-muted/20 p-3">
				<div class="flex flex-wrap items-baseline gap-x-2 gap-y-1">
					{#if previewLoading && !preview}
						<Skeleton class="h-6 w-40" />
					{:else if preview}
						<span class="text-lg leading-6 font-semibold tabular-nums">
							{preview.total.toLocaleString()}
						</span>
						<span class="text-xs text-muted-foreground"> checks selected </span>
					{/if}
				</div>

				{#if preview && preview.total > 0}
					<SeverityBar counts={severityCounts} height="h-1.5" />
					<div class="flex flex-wrap gap-x-3 gap-y-1">
						{#each severityCounts as part (part.severity)}
							<span class="flex items-center gap-1 text-2xs text-muted-foreground">
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
					<p class="text-2xs text-warning">{warning}</p>
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
							<p class="text-2xs font-medium text-muted-foreground">Severity</p>
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
							<p class="text-2xs font-medium text-muted-foreground">Check sets</p>
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
