<script lang="ts">
	import type { Target } from '$lib/types/target';
	import type { TargetDetailRead } from '$lib/types/target-detail';
	import { buildTargetSummary, type PostureStatus } from './derive';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { CircleCheck, TriangleAlert, CircleX, Info } from 'lucide-svelte';

	interface Props {
		target: Target;
		detail: TargetDetailRead | null;
		loading?: boolean;
	}

	let { target, detail, loading = false }: Props = $props();

	const summary = $derived(buildTargetSummary(target, detail));

	const ICON: Record<PostureStatus, typeof Info> = {
		pass: CircleCheck,
		warn: TriangleAlert,
		fail: CircleX,
		info: Info,
		pending: Info
	};
	const COLOR: Record<PostureStatus, string> = {
		pass: 'text-muted-foreground/45',
		warn: 'text-amber-600 dark:text-amber-500',
		fail: 'text-destructive',
		info: 'text-muted-foreground/35',
		pending: 'text-chart-1/70'
	};

	const ORDER: Record<PostureStatus, number> = { fail: 0, warn: 1, pending: 2, pass: 3, info: 4 };
	const items = $derived([...summary.posture].sort((a, b) => ORDER[a.status] - ORDER[b.status]));
</script>

<div class="rounded-lg border bg-card overflow-hidden">
	<div class="flex items-center justify-between px-4 py-2.5 border-b border-border/50">
		<h3 class="text-xs font-semibold tracking-tight text-foreground/90">Security posture</h3>
		{#if items.length > 0}
			<span class="text-[10px] font-mono tabular-nums text-muted-foreground/40">
				{items.filter((i) => i.status === 'fail' || i.status === 'warn').length} to review
			</span>
		{/if}
	</div>

	<div class="divide-y divide-border/15">
		{#if loading && items.length === 0}
			<div class="flex items-center gap-2 px-4 py-6 text-muted-foreground/50">
				<Spinner class="h-3.5 w-3.5" />
				<span class="text-[11px]">Evaluating signals…</span>
			</div>
		{:else if items.length === 0}
			<p class="px-4 py-6 text-center text-[11px] text-muted-foreground/50">
				No passive signals available yet.
			</p>
		{:else}
			{#each items as item (item.key)}
				{@const Icon = ICON[item.status]}
				<div class="flex items-start gap-2.5 px-4 py-2">
					{#if item.status === 'pending'}
						<Spinner class="h-3.5 w-3.5 mt-px shrink-0 text-chart-1/70" />
					{:else}
						<Icon class="h-3.5 w-3.5 mt-px shrink-0 {COLOR[item.status]}" />
					{/if}
					<div class="min-w-0">
						<p class="text-[11px] leading-snug text-foreground">{item.label}</p>
						{#if item.detail}
							<p class="text-[10px] leading-snug text-muted-foreground/50 break-words">{item.detail}</p>
						{/if}
					</div>
				</div>
			{/each}
		{/if}
	</div>
</div>
