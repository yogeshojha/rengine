<script lang="ts">
	import { toast } from 'svelte-sonner';
	import MessagesSquare from '@lucide/svelte/icons/messages-square';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { Button } from '$lib/components/ui/button';
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { estateApi } from '$lib/api/ask';
	import { relativeTime } from '$lib/utilities/dates';
	import { scopeLabel } from './link-scope';
	import { cn } from '$lib/utils.js';
	import type { EstateThread } from '$lib/types/ask';

	interface Props {
		open: boolean;
		threads: EstateThread[];
		loading: boolean;
		active: string | null;
		onOpenChange: (open: boolean) => void;
		onPick: (id: string) => void;
		onDeleted: (id: string) => void;
	}

	let { open, threads, loading, active, onOpenChange, onPick, onDeleted }: Props = $props();

	let pending = $state<EstateThread | null>(null);
	let deleting = $state(false);

	async function remove() {
		if (!pending || deleting) return;
		const id = pending.id;
		deleting = true;
		try {
			await estateApi.remove(id);
			onDeleted(id);
			pending = null;
		} catch (e) {
			toast.error((e as Error).message);
		} finally {
			deleting = false;
		}
	}
</script>

<Sheet.Root {open} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-lg">
		<Sheet.Header class="border-b px-5 py-4">
			<Sheet.Title>History</Sheet.Title>
		</Sheet.Header>
		<ScrollArea class="min-h-0 flex-1">
			<div class="px-3 py-3">
				{#if loading && !threads.length}
					<div class="flex flex-col gap-2 px-2">
						{#each { length: 5 } as _, i (i)}
							<Skeleton class="h-12 w-full" />
						{/each}
					</div>
				{:else if !threads.length}
					<EmptyState icon={MessagesSquare} title="No questions" compact />
				{:else}
					<ul class="flex flex-col gap-0.5">
						{#each threads as t (t.id)}
							<li
								class={cn(
									'group flex items-center gap-2 rounded-lg pr-1 hover:bg-muted/50',
									t.id === active && 'bg-muted'
								)}
							>
								<button
									type="button"
									class="flex min-w-0 flex-1 flex-col gap-0.5 px-3 py-2 text-left"
									onclick={() => onPick(t.id)}
								>
									<span class="truncate text-sm font-medium">{t.title}</span>
									<span class="flex flex-wrap gap-x-2 text-xs text-muted-foreground tabular-nums">
										<span>{scopeLabel(t.scope)}</span>
										<span>{relativeTime(t.last_at)}</span>
									</span>
								</button>
								<Hint text="Delete">
									{#snippet child(props)}
										<Button
											{...props}
											variant="ghost"
											size="icon-sm"
											class="text-muted-foreground opacity-0 group-hover:opacity-100 pointer-coarse:opacity-100 hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100"
											onclick={() => (pending = t)}
											aria-label="Delete {t.title}"
										>
											<Trash2 class="size-3.5" />
										</Button>
									{/snippet}
								</Hint>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		</ScrollArea>
	</Sheet.Content>
</Sheet.Root>

<ConfirmDialog
	open={pending !== null}
	title="Delete thread"
	description={pending ? `Thread "${pending.title}" and its answers are removed.` : ''}
	confirmLabel="Delete"
	loadingLabel="Deleting"
	loading={deleting}
	destructive
	onOpenChange={(o) => {
		if (!o) pending = null;
	}}
	onConfirm={() => void remove()}
/>
