<script lang="ts">
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { scanTabs } from '$lib/stores/scan-tabs.svelte';
	import { PINNED_SCAN_TABS, type ScanTab, type ScanTabSpec } from '$lib/config/scan-tabs';

	interface Row extends ScanTabSpec {
		defaultOn: boolean;
		count: number | null;
	}

	interface Props {
		rows: Row[];
		onToggle?: (key: ScanTab, visible: boolean) => void;
	}

	let { rows, onToggle }: Props = $props();

	function toggle(row: Row, visible: boolean) {
		if (visible) scanTabs.show(row.key);
		else scanTabs.hide(row.key);
		onToggle?.(row.key, visible);
	}
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger>
		{#snippet child({ props })}
			<Button
				{...props}
				variant="ghost"
				size="icon-sm"
				class="shrink-0 text-muted-foreground"
				aria-label="Show or hide tabs"
			>
				<Ellipsis class="size-4" />
			</Button>
		{/snippet}
	</DropdownMenu.Trigger>
	<DropdownMenu.Content align="end" class="max-h-none w-60 overflow-visible">
		<DropdownMenu.Label class="text-2xs font-mono tracking-[0.1em] text-muted-foreground uppercase">
			Tabs
		</DropdownMenu.Label>
		<ScrollArea class="[&_[data-slot=scroll-area-viewport]]:max-h-80">
			{#each rows.filter((r) => !PINNED_SCAN_TABS.includes(r.key)) as row (row.key)}
				<DropdownMenu.CheckboxItem
					checked={scanTabs.visible(row.key, row.defaultOn)}
					closeOnSelect={false}
					onCheckedChange={(v) => toggle(row, v)}
				>
					<span class="flex min-w-0 flex-1 items-center gap-2">
						<row.icon class="size-3.5 shrink-0 text-muted-foreground" />
						<span class="truncate">{row.label}</span>
					</span>
					{#if row.count != null}
						<span class="text-2xs tabular-nums text-muted-foreground">
							{row.count.toLocaleString()}
						</span>
					{/if}
				</DropdownMenu.CheckboxItem>
			{/each}
		</ScrollArea>
		<DropdownMenu.Separator />
		<DropdownMenu.Item disabled={!scanTabs.customized} onSelect={() => scanTabs.reset()}>
			Reset
		</DropdownMenu.Item>
	</DropdownMenu.Content>
</DropdownMenu.Root>
