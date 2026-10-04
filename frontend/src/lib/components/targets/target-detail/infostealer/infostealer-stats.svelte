<script lang="ts">
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import Handshake from '@lucide/svelte/icons/handshake';
	import Hint from '$lib/components/hint.svelte';
	import { AUDIENCE, Audience } from '$lib/config/infostealer';
	import type { IconComponent } from '$lib/config/icons';
	import type { InfostealerReport } from '$lib/types/infostealer';
	import { formatDateTime, relativeTimeLong } from '$lib/utilities/dates';

	interface Props {
		report: InfostealerReport;
	}

	let { report }: Props = $props();

	interface Stat {
		key: string;
		label: string;
		icon: IconComponent;
		value: string;
		when?: string | null;
	}

	let counts = $derived<Stat[]>([
		{
			key: 'employees',
			label: AUDIENCE[Audience.EMPLOYEE].label,
			icon: AUDIENCE[Audience.EMPLOYEE].icon,
			value: report.employees.toLocaleString()
		},
		{
			key: 'users',
			label: AUDIENCE[Audience.USER].label,
			icon: AUDIENCE[Audience.USER].icon,
			value: report.users.toLocaleString()
		},
		{
			key: 'third',
			label: 'Third parties',
			icon: Handshake,
			value: report.third_parties.toLocaleString()
		}
	]);
	let dates = $derived<Stat[]>(
		[
			{
				key: 'last-employee',
				label: 'Last employee infection',
				icon: CalendarClock,
				value: report.last_employee_at ? relativeTimeLong(report.last_employee_at) : '',
				when: report.last_employee_at
			},
			{
				key: 'last-user',
				label: 'Last user infection',
				icon: CalendarClock,
				value: report.last_user_at ? relativeTimeLong(report.last_user_at) : '',
				when: report.last_user_at
			}
		].filter((s) => s.when)
	);
</script>

<div
	class="grid grid-cols-2 overflow-hidden rounded-xl border bg-card sm:grid-cols-3 {dates.length
		? 'xl:grid-cols-5'
		: ''}"
>
	{#each [...counts, ...dates] as s (s.key)}
		<div class="-mr-px -mb-px flex min-w-0 flex-col gap-1.5 border-r border-b px-4 py-3.5">
			<span
				class="flex items-center gap-1.5 text-2xs tracking-wide text-muted-foreground uppercase"
			>
				<s.icon class="size-3.5 shrink-0" strokeWidth={1.75} aria-hidden="true" />
				<span class="truncate">{s.label}</span>
			</span>
			{#if s.when}
				<Hint text={formatDateTime(s.when)}>
					{#snippet child(props)}
						<span {...props} class="text-base leading-6 font-semibold">{s.value}</span>
					{/snippet}
				</Hint>
			{:else}
				<span class="text-lg leading-7 font-semibold tabular-nums">{s.value}</span>
			{/if}
		</div>
	{/each}
</div>
