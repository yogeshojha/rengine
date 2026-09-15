<script lang="ts">
	import Globe from '@lucide/svelte/icons/globe';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import * as Sheet from '$lib/components/ui/sheet';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import SectionHead from '$lib/components/section-head.svelte';
	import CodeBlock from '$lib/components/code-block.svelte';
	import { relativeTimeLong } from '$lib/utilities/dates';
	import { contextLang, metaLabel } from '$lib/utilities/secrets';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { STATE_BADGE, STATE_LABELS, SOURCE_LABELS } from '$lib/config/secrets';
	import type { SecretDetail } from '$lib/types/secret';

	interface Props {
		scanId: string;
		row: SecretDetail | null;
		open: boolean;
		onOpenChange: (open: boolean) => void;
	}

	let { scanId, row, open, onOpenChange }: Props = $props();

	const DT = 'text-2xs tracking-wide text-muted-foreground uppercase';
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];

	let lang = $derived(contextLang(row?.context));
	let assetHref = $derived(
		row ? ROUTES.results(WEB.tab, scanId || null, { [WEB.queryParam]: `name="${row.host}"` }) : ''
	);
	let claims = $derived.by(() => {
		const meta = row?.meta ?? {};
		return Object.entries(meta).filter(([, v]) => v !== null && v !== undefined && v !== '');
	});
	let sightingsCount = $derived(
		row && row.sightings_truncated
			? `${row.sightings_shown.length} of ${row.sightings.toLocaleString()}`
			: row && row.sightings > 1
				? row.sightings.toLocaleString()
				: null
	);
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
		{#if row}
			<Sheet.Header class="gap-2 border-b px-5 py-4">
				<div class="flex flex-wrap items-center gap-2">
					<Badge variant={STATE_BADGE[row.state] ?? 'outline'}>
						{STATE_LABELS[row.state] ?? row.state}
					</Badge>
					<Sheet.Title class="text-base">{row.kind_label}</Sheet.Title>
					{#if row.vendor}<span class="text-xs text-muted-foreground">{row.vendor}</span>{/if}
				</div>
				<Sheet.Description class="truncate font-mono text-xs">{row.url}</Sheet.Description>
				<div class="pt-1">
					<Button variant="outline" size="sm" href={assetHref} class="gap-1.5">
						Open web asset <ArrowUpRight class="size-3.5" />
					</Button>
				</div>
			</Sheet.Header>

			<ScrollArea class="min-h-0 flex-1">
				<div class="flex flex-col gap-6 px-5 py-5">
					<CodeBlock
						code={row.value}
						lang="text"
						label="Value"
						numbers={false}
						wrap={true}
						maxLines={12}
					/>

					{#if claims.length}
						<section class="flex flex-col gap-2.5">
							<SectionHead title="Decoded" />
							<dl class="overflow-hidden rounded-lg border text-sm">
								{#each claims as [key, value], i (key)}
									<div class="flex items-baseline gap-4 px-3.5 py-2 {i > 0 ? 'border-t' : ''}">
										<dt class="w-24 shrink-0 text-xs text-muted-foreground">{metaLabel(key)}</dt>
										<dd class="min-w-0 flex-1 font-mono text-xs break-all">
											{typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
										</dd>
									</div>
								{/each}
							</dl>
						</section>
					{/if}

					{#if row.context}
						<section class="flex flex-col gap-2.5">
							<SectionHead title="Context" />
							<CodeBlock
								code={row.context}
								{lang}
								label={row.source_label}
								maxLines={8}
								maxHeight="24rem"
								wrap={false}
								numbers={false}
								marks={[row.value]}
							/>
						</section>
					{/if}

					<section class="flex flex-col gap-2">
						<SectionHead title="Sightings" count={sightingsCount} />
						{#if row.sightings_shown.length}
							<ul class="flex flex-col divide-y divide-border/60 rounded-md border">
								{#each row.sightings_shown as s (s.id)}
									<li class="flex items-start gap-2 px-3 py-2">
										<Globe class="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
										<div class="flex min-w-0 flex-col">
											<span class="font-mono text-xs break-all">{s.url}</span>
											<span class="text-2xs text-muted-foreground">
												{SOURCE_LABELS[s.source] ?? s.source_label}
											</span>
										</div>
									</li>
								{/each}
							</ul>
						{:else}
							<div class="flex items-start gap-2 rounded-md border px-3 py-2">
								<Globe class="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
								<div class="flex min-w-0 flex-col">
									<span class="font-mono text-xs break-all">{row.url}</span>
									<span class="text-2xs text-muted-foreground">{row.source_label}</span>
								</div>
							</div>
						{/if}
					</section>

					<section class="flex flex-col gap-2">
						<SectionHead title="Detail" />
						<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
							<dt class={DT}>Family</dt>
							<dd>{row.group_label}</dd>
							{#if row.target_value}
								<dt class={DT}>Target</dt>
								<dd>{row.target_value}</dd>
							{/if}
							{#if row.hosts > 1}
								<dt class={DT}>Web assets</dt>
								<dd>{row.hosts.toLocaleString()}</dd>
							{/if}
							<dt class={DT}>Read from</dt>
							<dd>{row.source_label}</dd>
							<dt class={DT}>Seen</dt>
							<dd>{relativeTimeLong(row.discovered_at)}</dd>
						</dl>
					</section>
				</div>
			</ScrollArea>
		{/if}
	</Sheet.Content>
</Sheet.Root>
