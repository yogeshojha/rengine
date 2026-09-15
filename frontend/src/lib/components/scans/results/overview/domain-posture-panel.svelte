<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import Fingerprint from '@lucide/svelte/icons/fingerprint';
	import {
		CHECK_BY_KEY,
		FACT_CHIP,
		TONE_DOT,
		isSpoofable,
		postureQuery,
		sortChecks,
		zoneFacts
	} from '$lib/config/domain-posture';
	import type { DomainPostureSummary } from '$lib/types/domain-posture';

	interface Props {
		summary: DomainPostureSummary | null;
		loading: boolean;
		onFilter: (search: string) => void;
	}

	let { summary, loading, onFilter }: Props = $props();

	const SCROLL_AFTER = 8;
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	let zones = $derived(summary?.zones ?? []);
	let hasData = $derived((summary?.evaluated ?? 0) > 0);
	let tall = $derived(zones.length > SCROLL_AFTER);
</script>

{#if (loading && !summary) || hasData}
	<Card.Root class="gap-0 overflow-hidden py-0">
		<PanelHead
			title="Domain posture"
			description="SPF, DMARC, DKIM, MTA-STS, DNSSEC and CAA per zone"
		>
			{#if summary}
				<span class="tabular-nums">{plural(summary.evaluated, 'zone', 'zones')}</span>
				{#if summary.warning > 0}
					<span class="flex items-center gap-1.5 tabular-nums">
						<span class="size-1.5 rounded-full {TONE_DOT.warning}" aria-hidden="true"></span>
						{summary.warning.toLocaleString()} warning
					</span>
				{/if}
				{#if summary.info > 0}
					<span class="flex items-center gap-1.5 tabular-nums">
						<span class="size-1.5 rounded-full {TONE_DOT.info}" aria-hidden="true"></span>
						{summary.info.toLocaleString()} info
					</span>
				{/if}
				{#if summary.spoofable > 0}
					<span class="tabular-nums">{summary.spoofable.toLocaleString()} spoofable</span>
				{/if}
			{/if}
		</PanelHead>

		{#if !summary}
			<div class="flex flex-col gap-3 p-5">
				{#each Array(3) as _, i (i)}
					<Skeleton class="h-12 w-full" />
				{/each}
			</div>
		{:else}
			<ScrollArea class={tall ? 'h-96' : ''}>
				<ul class="flex flex-col divide-y">
					{#each zones as z (z.zone)}
						{@const issues = sortChecks(z.posture_issues)}
						{@const facts = zoneFacts(z)}
						<li class="flex flex-col gap-2 px-5 py-3">
							<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
								<span class="font-mono text-sm">{z.zone}</span>
								<span class="text-xs text-muted-foreground tabular-nums">
									{plural(z.hosts, 'web asset', 'web assets')}
								</span>
								{#if isSpoofable(issues)}
									<span class="text-xs text-warning">Spoofable</span>
								{/if}
							</div>
							<div class="flex flex-wrap gap-1">
								{#each facts as f (f.key)}
									<Hint text={f.hint}>
										{#snippet child(props)}
											<span
												{...props}
												class="inline-flex h-5 items-center gap-1 rounded-sm border px-1.5 text-2xs {FACT_CHIP[
													f.tone
												]}"
											>
												<span class="opacity-70">{f.label}</span>
												<span class="font-mono">{f.value}</span>
											</span>
										{/snippet}
									</Hint>
								{/each}
							</div>
							{#if issues.length}
								<ul class="flex flex-wrap gap-1">
									{#each issues as key (key)}
										{@const spec = CHECK_BY_KEY[key]}
										<li>
											<Tooltip.Root>
												<Tooltip.Trigger>
													{#snippet child({ props })}
														<button
															{...props}
															type="button"
															class="inline-flex h-6 items-center gap-1.5 rounded-md border border-border px-2 text-xs transition-colors hover:bg-muted/50"
															onclick={() => onFilter(postureQuery(key))}
														>
															<span
																class="size-1.5 rounded-full {spec
																	? TONE_DOT[spec.tone]
																	: 'bg-muted'}"
																aria-hidden="true"
															></span>
															{spec?.label ?? key}
														</button>
													{/snippet}
												</Tooltip.Trigger>
												<Tooltip.Content class="flex max-w-xs items-center gap-1.5">
													{z.evidence[key] ?? spec?.help ?? key}
													<Fingerprint class="size-3 opacity-60" />
													<span class="font-mono">{postureQuery(key)}</span>
												</Tooltip.Content>
											</Tooltip.Root>
										</li>
									{/each}
								</ul>
							{:else}
								<span class="text-xs text-muted-foreground">Passes every applicable check</span>
							{/if}
						</li>
					{/each}
				</ul>
			</ScrollArea>
		{/if}
	</Card.Root>
{/if}
