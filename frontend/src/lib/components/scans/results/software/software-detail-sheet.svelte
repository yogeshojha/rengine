<script lang="ts">
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Info from '@lucide/svelte/icons/info';
	import * as Sheet from '$lib/components/ui/sheet';
	import { Badge } from '$lib/components/ui/badge';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import CopyButton from '$lib/components/copy-button.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import TechIcon from '../tech-icon.svelte';
	import { relativeTimeLong } from '$lib/utilities/dates';
	import { SEVERITY_TEXT, severityLabel } from '$lib/config/vulnerabilities';
	import { CAVEAT_HELP, CONFIDENCE_HELP, CONFIDENCE_VARIANT } from '$lib/config/software';
	import type { SoftwareCve } from '$lib/types/software';

	interface Props {
		row: SoftwareCve | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
	}

	let { row, open, onOpenChange }: Props = $props();

	const NVD = 'https://nvd.nist.gov/vuln/detail/';
	const DT = 'text-2xs tracking-wide text-muted-foreground uppercase';
	let epss = $derived(row?.epss_score == null ? null : Math.round(row.epss_score * 100));
	let location = $derived(row ? (row.host ?? row.ip ?? '') : '');
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
		{#if row}
			<Sheet.Header class="gap-1 border-b px-5 py-4">
				<Sheet.Title class="flex items-center gap-2 font-mono text-base break-all">
					{row.cve}
					<a
						href={`${NVD}${row.cve}`}
						target="_blank"
						rel="noreferrer noopener"
						class="text-muted-foreground hover:text-foreground"
					>
						<ExternalLink class="size-3.5" />
					</a>
				</Sheet.Title>
				<Sheet.Description class="flex flex-wrap items-center gap-1.5">
					<span class={SEVERITY_TEXT[row.severity] ?? 'text-muted-foreground'}>
						{severityLabel(row.severity)}
					</span>
					{#if row.cvss_score != null}
						<span class="text-muted-foreground tabular-nums">CVSS {row.cvss_score.toFixed(1)}</span>
					{/if}
					{#if row.is_kev}
						<Badge variant="destructive" class="h-4 px-1 text-2xs">Known exploited</Badge>
					{/if}
					{#if row.kev_ransomware}
						<Badge variant="destructive" class="h-4 px-1 text-2xs">Ransomware</Badge>
					{/if}
				</Sheet.Description>
			</Sheet.Header>

			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col gap-5 px-5 py-4">
					<div class="rounded-md border border-border/60 bg-muted/30 px-3 py-2 text-xs">
						<div class="flex items-start gap-2">
							<Info class="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
							<p class="text-muted-foreground">
								Inferred from the reported version against the NVD corpus. No request was sent.
							</p>
						</div>
					</div>

					<section class="flex flex-col gap-2">
						<SectionHead title="Software" />
						<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
							<dt class={DT}>Reported as</dt>
							<dd class="flex items-center gap-1.5">
								<TechIcon name={row.name} class="size-3.5 shrink-0" />
								{row.name}
								<span class="text-muted-foreground">{row.version}</span>
							</dd>
							<dt class={DT}>NVD product</dt>
							<dd class="font-mono text-xs">{row.vendor}:{row.product}</dd>
							<dt class={DT}>CPE</dt>
							<dd class="flex items-start gap-1.5 font-mono text-2xs break-all">
								{row.cpe}
								<CopyButton value={row.cpe} />
							</dd>
							<dt class={DT}>Version from</dt>
							<dd>{row.version_source_label}</dd>
						</dl>
					</section>

					<section class="flex flex-col gap-2">
						<SectionHead title="Confidence" />
						<div class="flex flex-wrap items-center gap-1.5">
							<Badge variant={CONFIDENCE_VARIANT[row.confidence] ?? 'outline'}>
								{row.confidence_label}
							</Badge>
						</div>
						<p class="text-xs text-muted-foreground">{CONFIDENCE_HELP[row.confidence] ?? ''}</p>
						{#if row.caveats.length}
							<ul class="flex flex-col gap-2 pt-1">
								{#each row.caveats as caveat (caveat.kind)}
									<li class="flex flex-col gap-0.5">
										<span class="text-sm">{caveat.label}</span>
										<span class="text-xs text-muted-foreground">
											{CAVEAT_HELP[caveat.kind] ?? ''}
										</span>
									</li>
								{/each}
							</ul>
						{/if}
					</section>

					<section class="flex flex-col gap-2">
						<SectionHead title="Exploitation" />
						<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
							<dt class={DT}>EPSS</dt>
							<dd>
								{#if epss != null}
									<span class="tabular-nums">{epss}%</span>
									<span class="text-xs text-muted-foreground">in the next 30 days</span>
								{:else}
									<span class="text-muted-foreground">Not scored</span>
								{/if}
							</dd>
							<dt class={DT}>Rank</dt>
							<dd class="tabular-nums">{row.exploit_score}</dd>
							{#if row.kev_due_date}
								<dt class={DT}>CISA due</dt>
								<dd>{row.kev_due_date}</dd>
							{/if}
						</dl>
					</section>

					<section class="flex flex-col gap-2">
						<SectionHead title="Where" />
						<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
							<dt class={DT}>Asset</dt>
							<dd class="break-all">
								{location}{#if row.port}<span class="text-muted-foreground">:{row.port}</span>{/if}
							</dd>
							{#if row.url}
								<dt class={DT}>URL</dt>
								<dd class="break-all">{row.url}</dd>
							{/if}
							{#if row.target_value}
								<dt class={DT}>Target</dt>
								<dd>{row.target_value}</dd>
							{/if}
							<dt class={DT}>Seen</dt>
							<dd>{relativeTimeLong(row.discovered_at)}</dd>
						</dl>
					</section>

					{#if row.description}
						<section class="flex flex-col gap-2">
							<SectionHead title="NVD description" />
							<p class="text-sm leading-relaxed text-muted-foreground">{row.description}</p>
						</section>
					{/if}
				</div>
			</ScrollArea>
		{/if}
	</Sheet.Content>
</Sheet.Root>
