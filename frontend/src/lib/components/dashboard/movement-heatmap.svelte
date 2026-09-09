<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import Widget from './widget.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE_ORDER } from '$lib/config/surface';
	import { getTargetTypeIcon } from '$lib/config/icons';
	import type { TargetType } from '$lib/types/target';
	import { relativeTime } from '$lib/utilities/dates';
	import { windowText, type DashboardOverview, type DashboardWindow } from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		window: DashboardWindow;
		class?: string;
	}

	let { overview, window, class: className = '' }: Props = $props();

	const ROWS = 10;
	const MIN_WASH = 10;
	const MAX_WASH = 70;
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	let rows = $derived(overview.changes.slice(0, ROWS));
	let totals = $derived(new Map(overview.targets.map((t) => [t.id, t])));

	function cell(targetId: string, key: string, fresh: number) {
		const target = totals.get(targetId);
		const value = target?.surface.find((s) => s.key === key)?.value ?? 0;
		const ratio = value > 0 ? Math.min(1, fresh / value) : fresh > 0 ? 1 : 0;
		return { value, wash: fresh > 0 ? MIN_WASH + Math.sqrt(ratio) * (MAX_WASH - MIN_WASH) : 0 };
	}
</script>

<Widget
	title="Movement by target"
	description="What each target's runs in the {windowText(window)} were the first to report"
	class={className}
>
	<div class="overflow-x-auto">
		<table class="w-full border-separate border-spacing-0 text-sm">
			<thead>
				<tr class="text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
					<th class="px-5 py-2 text-left font-medium whitespace-nowrap">Target</th>
					{#each SURFACE_ORDER as spec (spec.key)}
						<th class="px-2 py-2 text-right font-medium whitespace-nowrap">
							<span class="inline-flex items-center gap-1.5">
								<spec.icon class="size-3.5" />
								<span class="hidden xl:inline">{spec.label}</span>
							</span>
						</th>
					{/each}
					<th class="px-5 py-2 text-right font-medium whitespace-nowrap">Last run</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as r (r.target_id)}
					{@const Icon = getTargetTypeIcon(r.target_type as TargetType, true)}
					<tr class="border-t">
						<td class="border-t px-5 py-2">
							<a
								href={ROUTES.target(r.target_id)}
								class="flex items-center gap-2 font-mono text-xs hover:underline"
							>
								<Icon class="size-3.5 shrink-0 text-muted-foreground" />
								<span class="truncate">{r.target_value}</span>
							</a>
							<a
								href={ROUTES.scan(r.last_scan_id)}
								class="ml-[22px] block text-[11px] text-muted-foreground hover:underline"
							>
								{plural(r.runs, 'run', 'runs')} · last {relativeTime(r.last_at)}{r.gone_web_assets >
								0
									? ` · ${r.gone_web_assets} gone`
									: ''}
							</a>
						</td>
						{#each SURFACE_ORDER as spec (spec.key)}
							{@const fresh = r.new[spec.key] ?? 0}
							{@const c = cell(r.target_id, spec.key, fresh)}
							{@const scanId = r.new_scan[spec.key]}
							{@const baseline = r.first.includes(spec.key)}
							<td class="border-t p-1">
								{#if fresh > 0}
									<Hint
										text="{plural(
											fresh,
											`new ${spec.noun}`,
											`new ${spec.nounPlural}`
										)} of {c.value.toLocaleString()}{scanId
											? ''
											: ` · across ${plural(r.runs, 'run', 'runs')}`}"
									>
										{#snippet child(props)}
											<svelte:element
												this={scanId ? 'a' : 'span'}
												{...props}
												href={scanId
													? ROUTES.scanTab(scanId, spec.tab, { [spec.queryParam]: 'is:new' })
													: undefined}
												class="flex h-8 items-center justify-end rounded-md px-2 text-xs font-semibold tabular-nums {scanId
													? 'hover:ring-1 hover:ring-primary/40'
													: ''}"
												style="background:color-mix(in oklch, var(--chart-1) {c.wash}%, transparent)"
											>
												▲ {fresh.toLocaleString()}
											</svelte:element>
										{/snippet}
									</Hint>
								{:else if baseline}
									<Hint text="First run to cover {spec.nounPlural}, so nothing counts as new yet">
										{#snippet child(props)}
											<span
												{...props}
												class="flex h-8 items-center justify-end rounded-md border border-dashed px-2 text-[11px] text-muted-foreground"
											>
												baseline
											</span>
										{/snippet}
									</Hint>
								{:else}
									<span
										class="flex h-8 items-center justify-end px-2 text-xs text-muted-foreground/50"
										>—</span
									>
								{/if}
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
	{#snippet footer()}
		Shade is the share of the target's {SURFACE_ORDER[0].nounPlural} that are new. A cell opens the run's
		new rows; a sum across runs cannot, so it stays unlinked.
	{/snippet}
</Widget>
