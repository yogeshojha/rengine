<script lang="ts">
	import {
		activityStatusIcon,
		activityStatusClass,
		ACTIVITY_STATUS_LABEL,
		durationText
	} from '$lib/utilities/scan-status';
	import type { ScanActivityRead } from '$lib/types/scan';

	interface Props {
		activities: ScanActivityRead[];
	}

	let { activities }: Props = $props();

	const HIDDEN_COUNT_KEYS = new Set(['excluded']);

	function countSummary(result: Record<string, number | string>): string {
		return Object.entries(result ?? {})
			.filter(([k, v]) => typeof v === 'number' && !HIDDEN_COUNT_KEYS.has(k))
			.map(([k, v]) => `${v} ${k}`)
			.join(' · ');
	}
</script>

<ol class="space-y-2">
	{#each activities as a (a.id)}
		{@const Icon = activityStatusIcon(a.status)}
		{@const summary = countSummary(a.result)}
		<li class="flex items-start gap-3 rounded-md border border-border p-3">
			<Icon
				class="mt-0.5 h-4 w-4 shrink-0 {activityStatusClass(a.status)} {a.status === 'running'
					? 'animate-spin'
					: ''}"
			/>
			<div class="min-w-0 flex-1">
				<div class="flex items-center justify-between gap-2">
					<span class="text-sm font-medium">{a.title}</span>
					<span class="text-xs {activityStatusClass(a.status)}"
						>{ACTIVITY_STATUS_LABEL[a.status]}</span
					>
				</div>
				<div class="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
					{#if summary}<span>{summary}</span>{/if}
					{#if a.command_count}<span
							>{a.command_count} command{a.command_count === 1 ? '' : 's'}</span
						>{/if}
					{#if durationText(a.duration_seconds)}<span>{durationText(a.duration_seconds)}</span>{/if}
				</div>
				{#if a.error}<p class="mt-1 text-xs text-destructive">{a.error}</p>{/if}
			</div>
		</li>
	{/each}
</ol>
