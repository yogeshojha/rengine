<script lang="ts">
	import Cell from '$lib/components/cell.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Spinner } from '$lib/components/ui/spinner';
	import CopyButton from '$lib/components/copy-button.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import CountryFlag from '$lib/components/scans/results/country-flag.svelte';
	import { ROUTES } from '$lib/config/routes';
	import type { RailGroup, Tone } from './derive';

	interface Props {
		targetId: string;
		group: RailGroup;
		loading?: boolean;
		class?: string;
	}

	let { targetId, group, loading = false, class: className = '' }: Props = $props();

	const TONE: Record<Tone, string> = {
		neutral: '',
		good: '',
		warn: 'text-warning',
		bad: 'text-destructive'
	};
</script>

<Cell
	id={group.key}
	title={group.title}
	href={group.link ? ROUTES.target(targetId, group.link.tab) : undefined}
	hrefLabel={group.link?.label}
	class={className}
>
	{#snippet tools()}
		{#if group.pending}
			<span class="flex items-center gap-1.5 text-xs text-info"
				><Spinner class="size-3" /> Collecting</span
			>
		{/if}
	{/snippet}
	{#if group.note}
		<div class="text-sm {TONE[group.note.tone]}">
			{group.note.text}
			{#if group.note.detail}
				<span class="block text-xs text-muted-foreground wrap-anywhere">{group.note.detail}</span>
			{/if}
		</div>
	{/if}
	{#if loading && !group.rows.length && !group.note}
		<Skeleton class="h-4 w-48" />
		<Skeleton class="h-4 w-36" />
	{:else if !group.rows.length && !group.note}
		<span class="text-sm text-muted-foreground">No record</span>
	{/if}
	{#if group.rows.length}
		<dl class="flex flex-col gap-1.5">
			{#each group.rows as row (row.key)}
				<div class="group/row grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2 text-sm leading-[1.4]">
					<dt class="pt-px text-xs text-muted-foreground">{row.label}</dt>
					<dd class="flex min-w-0 flex-col wrap-anywhere {TONE[row.tone ?? 'neutral']}">
						<span class="flex min-w-0 items-center gap-1.5">
							{#if row.brand}
								<TechIcon name={row.brand} class="size-4 rounded-[4px]" />
							{/if}
							{#if row.flag}
								<CountryFlag code={row.flag} showCode={false} />
							{/if}
							<span class="min-w-0 {row.mono ? 'font-mono text-xs' : ''}">{row.value}</span>
							{#if row.copy}
								<span
									class="flex h-4 shrink-0 items-center opacity-100 transition-opacity sm:opacity-0 sm:group-hover/row:opacity-100"
								>
									<CopyButton value={row.copy} class="size-5" />
								</span>
							{/if}
						</span>
						{#if row.sub}
							<span class="text-xs text-muted-foreground">{row.sub}</span>
						{/if}
					</dd>
				</div>
			{/each}
		</dl>
	{/if}
</Cell>
