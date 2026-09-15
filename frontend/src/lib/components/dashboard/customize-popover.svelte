<script lang="ts">
	import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
	import { Button } from '$lib/components/ui/button';
	import * as Popover from '$lib/components/ui/popover';
	import { Switch } from '$lib/components/ui/switch';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import {
		DASHBOARD_ROW_LABELS,
		DASHBOARD_ROWS,
		DASHBOARD_WIDGETS
	} from '$lib/config/dashboard-widgets';
	import { dashboardLayout } from '$lib/stores/dashboard-layout.svelte';

	let open = $state(false);
	let rows = $derived(
		DASHBOARD_ROWS.map((row) => ({
			row,
			label: DASHBOARD_ROW_LABELS[row],
			widgets: DASHBOARD_WIDGETS.filter((w) => w.row === row && dashboardLayout.available(w))
		})).filter((r) => r.widgets.length)
	);
</script>

<Popover.Root bind:open>
	<Popover.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="outline" size="sm">
				<SlidersHorizontal class="size-4" />
				Customize
			</Button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content align="end" class="w-80 p-0">
		<ScrollArea class="max-h-[70vh] [&>[data-slot=scroll-area-viewport]]:max-h-[70vh]">
			<div class="flex flex-col gap-1 px-3 py-2">
				{#each rows as r (r.row)}
					<span class="mt-2 font-mono text-2xs tracking-[0.1em] text-muted-foreground uppercase">
						{r.label}
					</span>
					{#each r.widgets as w (w.id)}
						<label class="flex cursor-pointer items-center justify-between gap-3 py-1 text-sm">
							<span class="min-w-0 truncate">{w.label}</span>
							<Switch
								checked={dashboardLayout.visible(w.id)}
								onCheckedChange={(v) =>
									v ? dashboardLayout.show(w.id) : dashboardLayout.hide(w.id)}
								aria-label={w.label}
							/>
						</label>
					{/each}
				{/each}
			</div>
		</ScrollArea>
		<div class="flex items-center justify-end border-t px-3 py-2 text-xs text-muted-foreground">
			<Button
				variant="ghost"
				size="sm"
				class="h-7 px-2 text-xs"
				disabled={!dashboardLayout.customized}
				onclick={() => dashboardLayout.reset()}
			>
				Reset
			</Button>
		</div>
	</Popover.Content>
</Popover.Root>
