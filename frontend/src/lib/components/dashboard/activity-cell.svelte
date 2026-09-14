<script lang="ts">
	import Cell from './cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { ActivityKind } from '$lib/config/dashboard';
	import { relativeTime } from '$lib/utilities/dates';
	import type { DashboardActivity, DashboardEvent } from '$lib/types/dashboard';

	interface Props {
		activity: DashboardActivity | null;
		loading?: boolean;
		class?: string;
	}

	let { activity, loading = false, class: className = '' }: Props = $props();

	const SHOWN = 10;
	let events = $derived((activity?.events ?? []).slice(0, SHOWN));
	const DOT: Record<DashboardEvent['tone'], string> = {
		neutral: 'bg-muted-foreground/60',
		hot: 'bg-destructive',
		new: 'bg-chart-1'
	};
	function href(e: DashboardEvent): string | null {
		switch (e.kind) {
			case ActivityKind.Run:
				return e.scan_id ? ROUTES.scan(e.scan_id) : null;
			case ActivityKind.Intel:
				return e.scan_id ? ROUTES.scanTab(e.scan_id, 'vulnerabilities') : null;
			case ActivityKind.Watch:
				return e.watch_id ? ROUTES.bountyWatch(e.watch_id) : null;
			case ActivityKind.Program:
				return e.handle ? ROUTES.bountyHub(e.handle, e.platform ?? undefined) : null;
			case ActivityKind.Connector:
				return ROUTES.connectors();
			default:
				return null;
		}
	}
</script>

<Cell
	id="activity"
	title="Activity"
	href={ROUTES.scans}
	hrefLabel="Scans"
	loading={loading && !activity}
	class={className}
	bodyClass="pt-1"
>
	{#if events.length}
		<ol class="flex flex-col">
			{#each events as e (`${e.kind}:${e.at}:${e.title}`)}
				{@const to = href(e)}
				<li class="border-t first:border-t-0">
					<svelte:element
						this={to ? 'a' : 'div'}
						href={to ?? undefined}
						class="grid grid-cols-[auto_3.5rem_1fr_auto] items-baseline gap-3 rounded-md py-1.5 text-sm transition-colors {to
							? '-mx-2 px-2 hover:bg-muted/40 hover:text-foreground'
							: ''}"
					>
						<span class="flex h-5 items-center">
							<span class="size-1.5 rounded-full {DOT[e.tone]}"></span>
						</span>
						<span class="text-xs text-muted-foreground tabular-nums">{relativeTime(e.at)}</span>
						<Hint text="{e.title}{e.detail ? ` · ${e.detail}` : ''}">
							{#snippet child(props)}
								<span {...props} class="min-w-0 truncate">
									<span class="font-medium">{e.title}</span>
									{#if e.detail}<span class="text-muted-foreground"> · {e.detail}</span>{/if}
								</span>
							{/snippet}
						</Hint>
						<span class="font-mono text-2xs tracking-[0.08em] text-muted-foreground uppercase">
							{e.label}
						</span>
					</svelte:element>
				</li>
			{/each}
		</ol>
	{:else}
		<span class="text-sm text-muted-foreground">No activity</span>
	{/if}
</Cell>
