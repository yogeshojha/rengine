<script lang="ts" module>
	export interface SheetRowAction {
		label: string;
		doneLabel: string;
		done?: boolean;
		pending?: boolean;
		onClick: () => void;
	}
	export interface SheetRow {
		key: string;
		primary: string;
		secondary?: string;
		meta?: string;
		href?: string;
		tone?: 'warn' | 'bad';
		group?: string;
		action?: SheetRowAction;
	}
	export interface SheetAction {
		label: string;
		onClick: () => void;
	}
</script>

<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Check from '@lucide/svelte/icons/check';
	import * as Sheet from '$lib/components/ui/sheet';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import LoadingButton from '$lib/components/loading-button.svelte';

	interface Props {
		open: boolean;
		onOpenChange: (open: boolean) => void;
		title: string;
		description?: string;
		rows: SheetRow[];
		action?: SheetAction | null;
	}

	let { open, onOpenChange, title, description, rows, action = null }: Props = $props();

	const TONE = { warn: 'text-warning', bad: 'text-destructive' };

	let groups = $derived.by(() => {
		const out: { label: string | undefined; rows: SheetRow[] }[] = [];
		for (const r of rows) {
			const last = out[out.length - 1];
			if (last && last.label === r.group) last.rows.push(r);
			else out.push({ label: r.group, rows: [r] });
		}
		return out;
	});
</script>

{#snippet body(r: SheetRow)}
	<span class="flex min-w-0 flex-1 flex-col gap-0.5">
		<span class="truncate font-mono text-xs leading-5">{r.primary}</span>
		{#if r.secondary}
			<span class="line-clamp-2 text-xs leading-4 text-muted-foreground wrap-anywhere">
				{r.secondary}
			</span>
		{/if}
	</span>
	{#if r.meta}
		<span
			class="flex h-5 shrink-0 items-center text-xs tabular-nums {r.tone
				? TONE[r.tone]
				: 'text-muted-foreground'}"
		>
			{r.meta}
		</span>
	{/if}
{/snippet}

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-md">
		<Sheet.Header class="border-b px-5 py-4 pr-12">
			<Sheet.Title class="text-base">{title}</Sheet.Title>
			{#if description}
				<Sheet.Description>{description}</Sheet.Description>
			{/if}
		</Sheet.Header>
		<ScrollArea class="min-h-0 flex-1">
			<div class="flex flex-col px-2 py-1">
				{#each groups as g, gi (g.label ?? gi)}
					{#if g.label}
						<span
							class="flex items-center justify-between px-3 pt-4 pb-1 text-[11px] font-medium tracking-wide text-muted-foreground uppercase"
						>
							{g.label}
							<span class="tabular-nums">{g.rows.length}</span>
						</span>
					{/if}
					<ul class="flex flex-col divide-y divide-border/60">
						{#each g.rows as r (r.key)}
							<li>
								{#if r.action}
									<div class="flex items-start gap-3 px-3 py-2.5">
										{@render body(r)}
										<span class="flex h-5 shrink-0 items-center">
											{#if r.action.done}
												<span class="flex items-center gap-1 text-xs text-success">
													<Check class="size-3.5" />
													{r.action.doneLabel}
												</span>
											{:else}
												<LoadingButton
													variant="outline"
													size="sm"
													class="h-6 px-2 text-xs"
													loading={r.action.pending}
													onclick={r.action.onClick}
												>
													{r.action.label}
												</LoadingButton>
											{/if}
										</span>
									</div>
								{:else if r.href}
									<a
										href={r.href}
										class="group flex items-start gap-3 rounded-md px-3 py-2.5 transition-colors hover:bg-muted/50"
									>
										{@render body(r)}
										<span class="flex h-5 shrink-0 items-center">
											<ArrowUpRight
												class="size-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
											/>
										</span>
									</a>
								{:else}
									<div class="flex items-start gap-3 px-3 py-2.5">{@render body(r)}</div>
								{/if}
							</li>
						{/each}
					</ul>
				{/each}
			</div>
		</ScrollArea>
		{#if action}
			<Sheet.Footer class="border-t px-5 py-4 sm:flex-row sm:justify-start">
				<Button size="sm" onclick={action.onClick}>{action.label}</Button>
			</Sheet.Footer>
		{/if}
	</Sheet.Content>
</Sheet.Root>
