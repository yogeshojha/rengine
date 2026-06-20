<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import * as Card from '$lib/components/ui/card';
	import { Separator } from '$lib/components/ui/separator';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import {
		AlertTriangle,
		CircleCheck,
		CircleSlash,
		KeyRound,
		Gauge,
		Cpu,
		Timer
	} from 'lucide-svelte';
	import type { PreviewTool, PreviewToolStatus, ScanPreview } from '$lib/types/scan';

	interface Props {
		preview: ScanPreview | null;
		loading?: boolean;
	}

	let { preview, loading = false }: Props = $props();

	const STATUS_LABEL: Record<PreviewToolStatus, string> = {
		will_run: 'Will run',
		skipped_disabled: 'Disabled',
		skipped_needs_key: 'Needs key'
	};

	function statusBadgeClass(status: PreviewToolStatus): string {
		// Monochrome-leaning: will_run foreground, disabled muted, needs-key a
		// restrained amber accent. No bright colors.
		if (status === 'will_run') return 'border-foreground/30 text-foreground';
		if (status === 'skipped_needs_key')
			return 'border-amber-500/40 text-amber-600 dark:text-amber-400';
		return 'border-border text-muted-foreground';
	}

	function summaryBool(v: boolean | null): string {
		if (v === null) return 'engine default';
		return v ? 'on' : 'off';
	}

	let s = $derived(preview?.summary ?? null);
</script>

{#if loading}
	<div class="space-y-3">
		{#each Array(3) as _, i (i)}
			<Skeleton class="h-28 rounded-lg border border-border" />
		{/each}
	</div>
{:else if !preview}
	<Empty.Root class="h-full min-h-[200px] gap-0 border border-border bg-muted/20 p-8">
		<Empty.Header class="gap-0">
			<Empty.Media class="mb-3">
				<Gauge class="h-8 w-8 text-muted-foreground" />
			</Empty.Media>
			<Empty.Title class="text-sm font-medium text-foreground">No preview yet</Empty.Title>
			<Empty.Description class="mt-1 text-xs text-muted-foreground">
				Select an engine and target to preview the resolved scan plan.
			</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else}
	<div class="space-y-4">
		<!-- Header -->
		<div class="flex flex-wrap items-center gap-2 text-sm">
			<span class="font-mono text-foreground">{preview.target_value}</span>
			<Badge variant="outline" class="font-normal">{preview.target_type}</Badge>
			<span class="text-muted-foreground">·</span>
			<span class="text-muted-foreground">{preview.engine_name}</span>
			{#if preview.context_name}
				<span class="text-muted-foreground">/ {preview.context_name}</span>
			{:else}
				<span class="text-muted-foreground italic">/ engine defaults</span>
			{/if}
		</div>

		<!-- Warnings -->
		{#if preview.warnings.length > 0}
			<div
				class="space-y-1 rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-400"
			>
				{#each preview.warnings as warning (warning)}
					<div class="flex items-start gap-2">
						<AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />
						<span>{warning}</span>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Phases -->
		{#each preview.phases as phase (phase.phase)}
			<Card.Root class="gap-0 py-0">
				<Card.Header class="px-4 py-3">
					<Card.Title class="text-sm font-semibold">{phase.label}</Card.Title>
				</Card.Header>
				<Separator />
				<Card.Content class="p-0">
					<ul class="divide-y divide-border">
						{#each phase.tools as tool (tool.capability)}
							{@const t = tool as PreviewTool}
							<li class="flex flex-col gap-1 px-4 py-2.5">
								<div class="flex items-center justify-between gap-2">
									<span
										class="text-sm {t.status === 'skipped_disabled'
											? 'text-muted-foreground'
											: 'text-foreground'}"
									>
										{t.label}
									</span>
									<Badge variant="outline" class="gap-1 font-normal {statusBadgeClass(t.status)}">
										{#if t.status === 'will_run'}
											<CircleCheck class="h-3 w-3" />
										{:else if t.status === 'skipped_needs_key'}
											<KeyRound class="h-3 w-3" />
										{:else}
											<CircleSlash class="h-3 w-3" />
										{/if}
										{STATUS_LABEL[t.status]}
									</Badge>
								</div>

								{#if t.status === 'will_run' && (t.rate != null || t.threads != null || t.timeout != null)}
									<div class="flex flex-wrap items-center gap-1.5">
										{#if t.rate != null}
											<Badge
												variant="secondary"
												class="gap-1 rounded px-1.5 py-0.5 text-[10px] font-normal text-muted-foreground"
											>
												<Gauge class="h-3 w-3" />{t.rate}/s
											</Badge>
										{/if}
										{#if t.threads != null}
											<Badge
												variant="secondary"
												class="gap-1 rounded px-1.5 py-0.5 text-[10px] font-normal text-muted-foreground"
											>
												<Cpu class="h-3 w-3" />{t.threads} threads
											</Badge>
										{/if}
										{#if t.timeout != null}
											<Badge
												variant="secondary"
												class="gap-1 rounded px-1.5 py-0.5 text-[10px] font-normal text-muted-foreground"
											>
												<Timer class="h-3 w-3" />{t.timeout}s
											</Badge>
										{/if}
									</div>
								{:else if t.reason}
									<span class="text-xs text-muted-foreground">{t.reason}</span>
								{/if}
							</li>
						{/each}
					</ul>
				</Card.Content>
			</Card.Root>
		{/each}

		<!-- Summary -->
		{#if s}
			<Card.Root class="gap-0 py-0">
				<Card.Header class="px-4 py-3">
					<Card.Title class="text-sm font-semibold">Resolved Configuration</Card.Title>
				</Card.Header>
				<Separator />
				<Card.Content class="space-y-3 p-4 text-sm">
					<div class="grid grid-cols-2 gap-x-4 gap-y-2">
						<div class="text-muted-foreground">Auth</div>
						<div class="text-foreground">
							{s.auth_summary === 'None' ? 'None' : `${s.auth_summary} ✓`}
						</div>

						<div class="text-muted-foreground">Custom headers</div>
						<div class="text-foreground">
							{#if s.custom_header_names.length > 0}
								<div class="flex flex-wrap gap-1">
									{#each s.custom_header_names as name (name)}
										<Badge variant="secondary" class="rounded px-1.5 py-0.5 text-[10px] font-mono font-normal">{name}</Badge>
									{/each}
								</div>
							{:else}
								<span class="text-muted-foreground">None</span>
							{/if}
						</div>

						<div class="text-muted-foreground">Rate limits</div>
						<div class="text-foreground">{s.rate_summary}</div>

						<div class="text-muted-foreground">Thread multiplier</div>
						<div class="text-foreground">×{s.thread_multiplier}</div>

						<div class="text-muted-foreground">Timeout multiplier</div>
						<div class="text-foreground">×{s.timeout_multiplier}</div>

						<div class="text-muted-foreground">HTTP protocol</div>
						<div class="text-foreground">{s.http_protocol}</div>

						<div class="text-muted-foreground">Follow redirects</div>
						<div class="text-foreground">{summaryBool(s.follow_redirects)}</div>

						{#if s.excluded_subdomains_count + s.excluded_paths_count + s.excluded_ips_count > 0}
							<div class="text-muted-foreground">Exclusions</div>
							<div class="text-foreground">
								{s.excluded_subdomains_count} subdomains, {s.excluded_paths_count} paths, {s.excluded_ips_count}
								IPs
							</div>
						{/if}

						{#if s.included_subdomains.length > 0}
							<div class="text-muted-foreground">Included subdomains</div>
							<div class="text-foreground">
								<div class="flex flex-wrap gap-1">
									{#each s.included_subdomains as sub (sub)}
										<Badge variant="secondary" class="rounded px-1.5 py-0.5 text-[10px] font-mono font-normal">{sub}</Badge>
									{/each}
								</div>
							</div>
						{/if}
					</div>

					<Separator />

					<div class="flex items-center gap-1.5 text-xs text-muted-foreground">
						<Timer class="h-3.5 w-3.5" />
						<span>~{s.estimated_duration_human} · advisory</span>
					</div>
				</Card.Content>
			</Card.Root>
		{/if}
	</div>
{/if}
