<script lang="ts">
	import { untrack } from 'svelte';
	import * as Select from '$lib/components/ui/select';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Button } from '$lib/components/ui/button';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';
	import { scanEnginesApi } from '$lib/api/scan-engines';
	import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import {
		targetTypeLabel,
		type EnginePreviewResult,
		type ScanEngine
	} from '$lib/types/scan-engine';
	import { MASK, type AuthConfig, type ScanContextCreate } from '$lib/types/scan-context';

	interface Props {
		draft: ScanContextCreate | null;
	}

	let { draft }: Props = $props();

	const DEBOUNCE_MS = 300;
	const SECRET_FOR_TYPE: Record<string, keyof AuthConfig> = {
		bearer: 'bearer_token',
		basic: 'basic_password',
		header: 'header_value',
		cookie: 'cookie_value',
		api_key: 'api_key_value'
	};

	let engineId = $state('');
	let targetType = $state('domain');
	let plain = $state<EnginePreviewResult | null>(null);
	let merged = $state<EnginePreviewResult | null>(null);
	let isLoading = $state(false);
	let error = $state<string | null>(null);

	const engines = $derived(scanEnginesStore.engines);
	const engine = $derived(engines.find((e) => e.id === engineId));

	$effect(() => {
		engineCatalogStore.fetch();
		const project = projectsStore.activeProject;
		if (!project) return;
		untrack(() => {
			if (scanEnginesStore.fetchedProjectId !== project.id && !scanEnginesStore.isLoading) {
				scanEnginesStore.fetchEngines(project.id);
			}
		});
	});

	$effect(() => {
		if (!engineId && engines.length) untrack(() => (engineId = engines[0].id));
	});

	function previewContext(d: ScanContextCreate): ScanContextCreate {
		const auth = { ...d.auth } as AuthConfig;
		const secret = SECRET_FOR_TYPE[d.auth_type];
		if (secret && !auth[secret]) auth[secret] = MASK;
		return {
			...d,
			auth,
			extra_headers: d.extra_headers.filter((h) => h.name.trim()),
			compare_baseline_scan_id: null,
			scan_only_new_assets: false
		};
	}

	$effect(() => {
		const selected = engine;
		const target = targetType;
		const snapshot = draft ? JSON.stringify(draft) : null;
		if (!selected || !snapshot) return;
		const timer = setTimeout(() => refresh(selected, target, JSON.parse(snapshot)), DEBOUNCE_MS);
		return () => clearTimeout(timer);
	});

	let token = 0;
	async function refresh(selected: ScanEngine, target_type: string, d: ScanContextCreate) {
		const mine = ++token;
		isLoading = true;
		error = null;
		try {
			const body = {
				target_type,
				intensity: selected.intensity,
				global_threads: selected.global_threads,
				stages: selected.stages ?? {}
			};
			const [base, withContext] = await Promise.all([
				scanEnginesApi.preview(body),
				scanEnginesApi.preview({ ...body, context: previewContext(d) })
			]);
			if (mine !== token) return;
			plain = base;
			merged = withContext;
		} catch (e) {
			if (mine === token) error = e instanceof Error ? e.message : 'Preview unavailable';
		} finally {
			if (mine === token) isLoading = false;
		}
	}

	interface Change {
		group: string;
		label: string;
		from: string | null;
		to: string;
	}

	function fieldTitle(stage: string, field: string): string {
		return engineCatalogStore.stage(stage)?.fields.find((f) => f.name === field)?.title ?? field;
	}

	function list(items: string[], max = 3): string {
		const shown = items.slice(0, max).join(', ');
		return items.length > max ? `${shown} +${items.length - max}` : shown;
	}

	const changes = $derived.by<Change[]>(() => {
		if (!plain || !merged) return [];
		const out: Change[] = [];
		const before = plain.resolved;
		const after = merged.resolved;

		const newHeaders = after.header_names.filter((h) => !before.header_names.includes(h));
		if (newHeaders.length) {
			out.push({ group: 'Requests', label: 'Headers injected', from: null, to: list(newHeaders) });
		}
		if (after.http_protocol !== before.http_protocol) {
			out.push({
				group: 'Requests',
				label: 'Protocol',
				from: before.http_protocol,
				to: after.http_protocol.replace('_', ' ')
			});
		}
		if (after.follow_redirects !== before.follow_redirects) {
			out.push({
				group: 'Requests',
				label: 'Follow redirects',
				from: before.follow_redirects == null ? 'engine default' : String(before.follow_redirects),
				to: after.follow_redirects ? 'always' : 'never'
			});
		}

		if (after.global_threads !== before.global_threads) {
			out.push({
				group: 'Throughput',
				label: 'Global threads',
				from: String(before.global_threads),
				to: String(after.global_threads)
			});
		}
		for (const [stage, config] of Object.entries(merged.resolved_stages)) {
			const base = plain.resolved_stages[stage] ?? {};
			const title = engineCatalogStore.stage(stage)?.title ?? stage;
			for (const [field, value] of Object.entries(config)) {
				if (JSON.stringify(base[field]) === JSON.stringify(value)) continue;
				out.push({
					group: 'Throughput',
					label: `${title} · ${fieldTitle(stage, field)}`,
					from: String(base[field]),
					to: String(value)
				});
			}
		}

		if (after.included_subdomains.length) {
			out.push({
				group: 'Scope',
				label: 'Only these hosts',
				from: null,
				to: list(after.included_subdomains)
			});
		}
		if (after.excluded_subdomains.length) {
			out.push({
				group: 'Scope',
				label: 'Skip subdomains matching',
				from: null,
				to: list(after.excluded_subdomains)
			});
		}
		if (after.excluded_paths.length) {
			out.push({ group: 'Scope', label: 'Skip paths', from: null, to: list(after.excluded_paths) });
		}
		if (after.excluded_ips.length) {
			out.push({ group: 'Scope', label: 'Skip IPs', from: null, to: list(after.excluded_ips) });
		}
		return out;
	});

	const groups = $derived.by(() => {
		const map: Record<string, Change[]> = {};
		for (const change of changes) (map[change.group] ??= []).push(change);
		return Object.entries(map);
	});
</script>

<div class="wrap">
	<div class="head">
		<span class="dim">Applied to</span>
		<Select.Root type="single" value={engineId} onValueChange={(v) => v && (engineId = v)}>
			<Select.Trigger
				class="h-6 w-auto max-w-[180px] gap-1 border-0 bg-muted px-2 text-xs font-medium shadow-none"
				aria-label="Engine to preview against"
			>
				<span class="truncate">{engine?.name ?? 'Pick an engine'}</span>
			</Select.Trigger>
			<Select.Content>
				{#each engines as e (e.id)}
					<Select.Item value={e.id} label={e.name}>{e.name}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		<span class="dim">against a</span>
		<Select.Root type="single" value={targetType} onValueChange={(v) => v && (targetType = v)}>
			<Select.Trigger
				class="h-6 w-auto min-w-[88px] gap-1 border-0 bg-muted px-2 text-xs font-medium shadow-none"
				aria-label="Target type"
			>
				{targetTypeLabel(targetType)}
			</Select.Trigger>
			<Select.Content>
				{#each engineCatalogStore.targetTypes as t (t)}
					<Select.Item value={t} label={targetTypeLabel(t)}>{targetTypeLabel(t)}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		<span class="dim">target</span>
		{#if isLoading}<Spinner size={11} class="text-muted-foreground" />{/if}
	</div>

	<ScrollArea class="min-h-0 flex-1">
		<div class="body">
			{#if error}
				<p class="err">{error}</p>
			{:else if !engines.length && scanEnginesStore.hasFetched}
				<p class="empty">Create a scan engine to preview how this context changes it.</p>
				<Button
					variant="outline"
					size="sm"
					class="mt-3 gap-1.5"
					onclick={() => goto(ROUTES.engines)}
				>
					Scan engines <ArrowRight size={13} />
				</Button>
			{:else if !plain || !merged}
				<div class="center"><Spinner size={14} class="text-muted-foreground" /></div>
			{:else if !changes.length}
				<p class="count">No overrides</p>
				<p class="empty">
					<strong>{engine?.name}</strong> runs with its own settings. Credentials, rate limits, scope
					rules and runtime overrides from this context appear here.
				</p>
			{:else}
				<p class="count">
					<strong>{changes.length}</strong>
					change{changes.length === 1 ? '' : 's'} to {engine?.name}
				</p>
				{#each groups as [group, items] (group)}
					<p class="group">{group}</p>
					{#each items as change (change.label + change.to)}
						<div class="row">
							<span class="label">{change.label}</span>
							<span class="delta">
								{#if change.from !== null}
									<span class="from">{change.from}</span>
									<ArrowRight size={11} class="arrow" />
								{/if}
								<span class="to">{change.to}</span>
							</span>
						</div>
					{/each}
				{/each}
			{/if}
		</div>
	</ScrollArea>
</div>

<style>
	.wrap {
		display: flex;
		flex-direction: column;
		min-height: 0;
		height: 100%;
	}
	.head {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-wrap: wrap;
		flex-shrink: 0;
		padding: 7px 14px;
		border-bottom: 1px solid var(--border);
		font-size: 12px;
	}
	.dim {
		color: var(--muted-foreground);
	}
	.body {
		padding: 12px 14px 20px;
	}
	.center {
		display: flex;
		justify-content: center;
		padding: 24px 0;
	}
	.empty,
	.err {
		font-size: 12px;
		line-height: 1.55;
		color: var(--muted-foreground);
	}
	.err {
		color: var(--destructive);
	}
	.count {
		font-size: 12px;
		color: var(--muted-foreground);
		margin-bottom: 6px;
	}
	.count strong {
		color: var(--foreground);
		font-weight: 600;
	}
	.group {
		font-size: 10px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--muted-foreground);
		margin: 14px 0 4px;
	}
	.row {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 12px;
		padding: 5px 0;
		border-bottom: 1px solid color-mix(in oklch, var(--border) 60%, transparent);
		font-size: 12px;
	}
	.row:last-child {
		border-bottom: none;
	}
	.label {
		color: var(--muted-foreground);
		min-width: 0;
	}
	.delta {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		flex-shrink: 0;
		max-width: 60%;
		font-family: var(--font-mono, ui-monospace, monospace);
		font-size: 11.5px;
		font-variant-numeric: tabular-nums;
	}
	.from {
		color: var(--muted-foreground);
		text-decoration: line-through;
		opacity: 0.7;
	}
	.delta :global(.arrow) {
		color: var(--muted-foreground);
		flex-shrink: 0;
	}
	.to {
		color: var(--foreground);
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
</style>
