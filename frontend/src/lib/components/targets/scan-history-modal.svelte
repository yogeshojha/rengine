<script lang="ts">
	import type { Target } from '$lib/types/target';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Separator } from '$lib/components/ui/separator';
	import { Clock, History } from 'lucide-svelte';
	import CopyButton from '@/components/copy-button.svelte';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import ArrowUpRightIcon from '@lucide/svelte/icons/arrow-up-right';

	interface Props {
		open: boolean;
		target: Target | null;
		onOpenChange: (open: boolean) => void;
	}

	let { open = $bindable(), target, onOpenChange }: Props = $props();
</script>

<Dialog.Root {open} {onOpenChange}>
	<Dialog.Content
		class="sm:max-w-[560px] gap-0 p-0 overflow-hidden"
		onOpenAutoFocus={(e) => e.preventDefault()}
	>
		{#if target}
			<div class="p-6 pb-4">
				<div class="flex items-center gap-3">
					<div class="flex items-center justify-center h-9 w-9 rounded-lg bg-muted">
						<History class="h-4 w-4 text-muted-foreground" />
					</div>
					<div class="min-w-0 flex-1">
						<div class="flex items-center justify-between">
							<Dialog.Title class="text-lg font-semibold">Scan History</Dialog.Title>
							<!-- DUMMY COunts for now -->
							<span class="text-xs text-muted-foreground">5 scans</span>
						</div>
						<div class="flex items-center gap-1.5 mt-0.5">
							<code class="text-xs font-mono text-muted-foreground truncate"
								>{target.target_value}</code
							>
							<CopyButton value={target.target_value} />
						</div>
					</div>
				</div>
			</div>

			<Separator />

			<!-- TODO: implement scan history fetching & rendering -->
			<Empty.Root>
				<Empty.Header>
					<Empty.Media variant="icon">
						<Clock class="h-4 w-4 text-muted-foreground" />
					</Empty.Media>
					<Empty.Title>No scans yet</Empty.Title>
					<Empty.Description>
						{target.target_value} hasn't been scanned. Run a scan to start
						discovering its attack surface.
					</Empty.Description>
				</Empty.Header>
			</Empty.Root>
		{/if}
	</Dialog.Content>
</Dialog.Root>
