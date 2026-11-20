<script lang="ts">
	import History from '@lucide/svelte/icons/history';
	import { SvelteSet } from 'svelte/reactivity';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import { AUDIENCE, Audience } from '$lib/config/infostealer';
	import type { InfostealerChange, InfostealerReport } from '$lib/types/infostealer';
	import { formatDateTime, formatShortDate, relativeTime } from '$lib/utilities/dates';

	interface Props {
		report: InfostealerReport;
	}

	let { report }: Props = $props();

	const SHOWN_HOSTS = 5;
	const open = new SvelteSet<string>();

	interface Count {
		audience: Audience;
		from: number;
		to: number;
	}

	function counts(change: InfostealerChange): Count[] {
		return [
			{ audience: Audience.EMPLOYEE, from: change.employees_from, to: change.employees_to },
			{ audience: Audience.USER, from: change.users_from, to: change.users_to }
		].filter((c) => c.to > c.from);
	}
</script>

<section class="overflow-hidden rounded-xl border bg-card">
	<div class="flex flex-col gap-0.5 px-4 pt-3.5 pb-3">
		<SectionHead title="Changes" icon={History} count={report.changes.length} />
		<p class="text-xs text-muted-foreground">Compromised machines and logins added per lookup</p>
	</div>
	<ul aria-label="Changes" class="border-t">
		{#each report.changes as change (change.id)}
			{@const expanded = open.has(change.id)}
			{@const hosts = expanded ? change.hosts : change.hosts.slice(0, SHOWN_HOSTS)}
			<li
				class="grid grid-cols-1 gap-x-4 gap-y-2 border-b px-4 py-3 last:border-b-0 sm:grid-cols-[7.5rem_minmax(0,1fr)]"
			>
				<Hint text={formatDateTime(change.checked_at)}>
					{#snippet child(props)}
						<span {...props} class="flex w-fit flex-col gap-0.5">
							<span class="text-sm font-medium">{formatShortDate(change.checked_at)}</span>
							<span class="text-2xs text-muted-foreground">{relativeTime(change.checked_at)}</span>
						</span>
					{/snippet}
				</Hint>
				<div class="flex min-w-0 flex-col gap-2">
					{#if counts(change).length}
						<div class="flex flex-wrap gap-x-6 gap-y-1">
							{#each counts(change) as c (c.audience)}
								{@const audience = AUDIENCE[c.audience]}
								<span class="flex items-center gap-1.5 text-sm">
									<span class="flex h-5 items-center text-muted-foreground">
										<audience.icon class="size-3.5" strokeWidth={1.75} aria-hidden="true" />
									</span>
									<span class="text-muted-foreground">{audience.label}</span>
									<span class="tabular-nums">
										{c.from.toLocaleString()} to {c.to.toLocaleString()}
									</span>
									<span class="font-medium tabular-nums">+{(c.to - c.from).toLocaleString()}</span>
								</span>
							{/each}
						</div>
					{/if}
					{#if hosts.length}
						<ul class="flex flex-col gap-1">
							{#each hosts as h (`${h.audience}|${h.host}`)}
								{@const audience = AUDIENCE[h.audience]}
								<li class="flex min-w-0 items-center gap-2 text-xs">
									<Hint text={audience.label}>
										{#snippet child(props)}
											<span {...props} class="flex h-5 shrink-0 items-center text-muted-foreground">
												<audience.icon class="size-3.5" strokeWidth={1.75} aria-hidden="true" />
											</span>
										{/snippet}
									</Hint>
									<span class="min-w-0 font-mono wrap-anywhere">{h.host}</span>
									{#if h.new}
										<Badge variant="outline" class="text-2xs font-normal">First listed</Badge>
									{/if}
									<span class="ml-auto shrink-0 text-muted-foreground tabular-nums">
										{#if h.new}
											{h.credentials_to.toLocaleString()}
										{:else}
											{h.credentials_from.toLocaleString()} to {h.credentials_to.toLocaleString()}
										{/if}
										{h.credentials_to === 1 ? 'credential' : 'credentials'}
									</span>
								</li>
							{/each}
						</ul>
						{#if change.hosts.length > SHOWN_HOSTS}
							<Button
								variant="ghost"
								size="sm"
								class="h-6 w-fit px-1.5 text-xs text-muted-foreground"
								aria-expanded={expanded}
								onclick={() => (expanded ? open.delete(change.id) : open.add(change.id))}
							>
								{expanded
									? 'Show fewer'
									: `Show ${(change.hosts.length - SHOWN_HOSTS).toLocaleString()} more`}
							</Button>
						{/if}
					{/if}
				</div>
			</li>
		{/each}
	</ul>
</section>
