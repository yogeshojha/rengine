<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Separator } from '$lib/components/ui/separator';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import Play from '@lucide/svelte/icons/play';
	import Copy from '@lucide/svelte/icons/copy';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import MoreHorizontal from '@lucide/svelte/icons/more-horizontal';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import ContextFacets from './context-facets.svelte';
	import type { ScanContextRead } from '$lib/types/scan-context';
	import { authBadgeLabel } from './context-summary';
	import { formatDistanceToNow } from '$lib/utilities/dates';

	interface Props {
		context: ScanContextRead;
		proxyName?: string | null;
		isSelected?: boolean;
		onSelect?: () => void;
		onEdit?: () => void;
		onRun?: () => void;
		onDuplicate?: () => void;
		onDelete?: () => void;
	}

	let {
		context,
		proxyName = null,
		isSelected = false,
		onSelect,
		onEdit,
		onRun,
		onDuplicate,
		onDelete
	}: Props = $props();

	const usage = $derived.by(() => {
		const parts: string[] = [];
		const scans = context.usage?.scans ?? 0;
		if (scans) parts.push(`${scans} scan${scans === 1 ? '' : 's'}`);
		if (context.last_used_at) parts.push(`used ${formatDistanceToNow(context.last_used_at)}`);
		return parts.length ? parts.join(' · ') : 'Never used';
	});
</script>

<Card.Root
	class="group relative gap-0 py-0 transition-colors hover:border-foreground/25 data-[selected=true]:border-primary/50 data-[selected=true]:bg-primary/5"
	data-selected={isSelected}
>
	<div class="flex items-start gap-3 px-4 pt-4">
		{#if onSelect}
			<div
				class="relative z-10 flex h-5 items-center opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100 data-[on=true]:opacity-100 [@media(hover:none)]:opacity-100"
				data-on={isSelected}
			>
				<Checkbox
					checked={isSelected}
					onCheckedChange={() => onSelect()}
					aria-label="Select {context.name}"
				/>
			</div>
		{/if}

		<div class="min-w-0 flex-1">
			<div class="flex flex-wrap items-center gap-2">
				<button
					type="button"
					class="truncate text-left text-sm font-semibold after:absolute after:inset-0 after:rounded-xl focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-ring"
					onclick={() => onEdit?.()}
				>
					{context.name}
				</button>
				<Badge variant={context.auth_type === 'none' ? 'outline' : 'secondary'} class="text-[10px]">
					{authBadgeLabel(context)}
				</Badge>
			</div>
			{#if context.description}
				<p class="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{context.description}</p>
			{/if}
		</div>

		<div class="relative z-10 -mt-1 -mr-2 flex items-center">
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="icon-sm"
							class="text-muted-foreground"
							aria-label="More actions for {context.name}"
						>
							<MoreHorizontal size={15} />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-40">
					<DropdownMenu.Item onclick={() => onDuplicate?.()}>
						<Copy size={13} />
						Duplicate
					</DropdownMenu.Item>
					<DropdownMenu.Separator />
					<DropdownMenu.Item variant="destructive" onclick={() => onDelete?.()}>
						<Trash2 size={13} />
						Delete
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>

	<div class="px-4 pt-4 pb-1">
		<ContextFacets {context} {proxyName} />
	</div>

	<Separator class="mt-3" />

	<div class="flex items-center justify-between gap-3 px-4 py-2">
		<span class="flex min-w-0 items-center gap-1.5 truncate text-[11px] text-muted-foreground">
			{#if context.usage?.schedules}
				<CalendarClock size={12} class="shrink-0" />
				{context.usage.schedules} schedule{context.usage.schedules === 1 ? '' : 's'}
				<span aria-hidden="true">·</span>
			{/if}
			{usage}
		</span>
		<Button
			variant="ghost"
			size="sm"
			class="relative z-10 h-7 gap-1.5 px-2 text-xs"
			onclick={() => onRun?.()}
		>
			<Play size={12} />
			Run
		</Button>
	</div>
</Card.Root>
