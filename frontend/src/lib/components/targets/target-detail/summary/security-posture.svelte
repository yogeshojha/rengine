<script lang="ts">
	import type { Target } from '$lib/types/target';
	import type { TargetDetailRead } from '$lib/types/target-detail';
	import { buildTargetSummary, type PostureStatus } from './derive';
	import * as Card from '$lib/components/ui/card';
	import PanelHead from '$lib/components/panel-head.svelte';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import Info from '@lucide/svelte/icons/info';
	import type { IconComponent } from '$lib/config/icons';

	interface Props {
		target: Target;
		detail: TargetDetailRead | null;
		loading?: boolean;
	}

	let { target, detail, loading = false }: Props = $props();

	const summary = $derived(buildTargetSummary(target, detail));

	const ICON: Record<PostureStatus, IconComponent> = {
		pass: CircleCheck,
		warn: TriangleAlert,
		fail: CircleX,
		info: Info,
		pending: Info
	};
	const COLOR: Record<PostureStatus, string> = {
		pass: 'text-success',
		warn: 'text-warning',
		fail: 'text-destructive',
		info: 'text-muted-foreground',
		pending: 'text-info'
	};

	const ORDER: Record<PostureStatus, number> = { fail: 0, warn: 1, pending: 2, pass: 3, info: 4 };
	const items = $derived([...summary.posture].sort((a, b) => ORDER[a.status] - ORDER[b.status]));
	const toReview = $derived(items.filter((i) => i.status === 'fail' || i.status === 'warn').length);
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead title="Posture" description="Signals derived from registration and DNS records">
		{#if items.length > 0}
			<span class="tabular-nums">
				{toReview === 0 ? 'Nothing to review' : `${toReview} to review`}
			</span>
		{/if}
	</PanelHead>

	{#if loading && items.length === 0}
		<div class="flex flex-col gap-3 px-5 py-4">
			{#each Array(4) as _, i (i)}
				<Skeleton class="h-5 w-full" />
			{/each}
		</div>
	{:else if items.length === 0}
		<p class="px-5 py-8 text-center text-sm text-muted-foreground">
			No passive signals available yet.
		</p>
	{:else}
		<ul class="divide-y">
			{#each items as item (item.key)}
				{@const Icon = ICON[item.status]}
				<li class="flex items-start gap-2.5 px-5 py-2.5">
					<span class="flex h-5 shrink-0 items-center">
						{#if item.status === 'pending'}
							<Spinner class="size-3.5 text-info" />
						{:else}
							<Icon class="size-3.5 {COLOR[item.status]}" />
						{/if}
					</span>
					<span class="flex min-w-0 flex-col">
						<span class="text-sm leading-5">{item.label}</span>
						{#if item.detail}
							<span class="text-xs leading-4 text-muted-foreground wrap-anywhere">
								{item.detail}
							</span>
						{/if}
					</span>
				</li>
			{/each}
		</ul>
	{/if}
</Card.Root>
