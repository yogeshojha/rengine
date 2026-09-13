<script lang="ts">
	import Waypoints from '@lucide/svelte/icons/waypoints';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import * as Popover from '$lib/components/ui/popover';
	import Hint from '$lib/components/hint.svelte';
	import { KIND_ICONS } from '$lib/config/correlation';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { cn } from '$lib/utils';
	import type { CrossLink } from '$lib/types/crosslink';
	import { linkedTargets } from '$lib/types/crosslink';

	interface Props {
		links: CrossLink[];
		onHost?: (host: string) => void;
		class?: string;
	}

	let { links, onHost, class: className }: Props = $props();

	let targets = $derived(linkedTargets(links));
	let label = $derived(
		targets.length === 1 ? `also on ${targets[0]}` : `also on ${targets.length} targets`
	);
	let heading = $derived(
		targets.length === 1
			? `Shared with ${targets[0]}`
			: `Shared with ${targets.length} other targets`
	);

	let open = $state(false);
	const stop = (e: Event) => e.stopPropagation();

	function surface(query: string) {
		return ROUTES.surface(SURFACE[SurfaceDimension.WEB_ASSETS].tab, { q: query });
	}
	function pick(host: string) {
		open = false;
		onHost?.(host);
	}
</script>

{#if links.length}
	<Popover.Root bind:open>
		<Popover.Trigger
			openOnHover
			openDelay={240}
			closeDelay={140}
			onclick={stop}
			onkeydown={stop}
			class={cn(
				'inline-flex h-5 shrink-0 cursor-pointer items-center gap-1 rounded-sm border border-primary/30 px-1.5 text-2xs text-primary hover:bg-primary/5',
				className
			)}
			aria-label={heading}
		>
			<Waypoints class="size-2.5" />
			{label}
		</Popover.Trigger>
		<Popover.Content class="w-80 p-0" align="start" onclick={stop}>
			<div class="border-b border-border px-3 py-2 text-xs font-medium">{heading}</div>
			<div class="flex flex-col divide-y divide-border">
				{#each links as link (link.kind + link.value)}
					{@const Icon = KIND_ICONS[link.kind] ?? Waypoints}
					<div class="p-2">
						<a
							href={surface(link.query)}
							class="group flex items-center gap-1.5 rounded-md px-1.5 py-1 hover:bg-accent"
							onclick={() => (open = false)}
						>
							<Icon class="size-3 shrink-0 text-muted-foreground" />
							<span class="shrink-0 text-2xs text-muted-foreground">{link.label}</span>
							<Hint text={link.value}>
								{#snippet child(props)}
									<span {...props} class="min-w-0 truncate font-mono text-2xs">{link.value}</span>
								{/snippet}
							</Hint>
							<ArrowUpRight
								class="size-2.5 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100"
							/>
						</a>
						<ul class="flex flex-col">
							{#each link.peers as peer (peer.host)}
								<li>
									{#if onHost}
										<button
											type="button"
											class="flex w-full items-center justify-between gap-2 rounded-md px-1.5 py-1 text-left hover:bg-accent"
											onclick={() => pick(peer.host)}
										>
											<span class="min-w-0 truncate font-mono text-xs">{peer.host}</span>
											<span class="shrink-0 text-2xs text-muted-foreground">
												{peer.target_value}
											</span>
											<ChevronRight class="size-3 shrink-0 text-muted-foreground" />
										</button>
									{:else}
										<div class="flex items-center justify-between gap-2 px-1.5 py-1">
											<span class="min-w-0 truncate font-mono text-xs">{peer.host}</span>
											<span class="shrink-0 text-2xs text-muted-foreground">
												{peer.target_value}
											</span>
										</div>
									{/if}
								</li>
							{/each}
						</ul>
						{#if link.hosts > link.peers.length}
							<p class="px-1.5 pt-1 text-2xs text-muted-foreground">
								{link.peers.length} of {link.hosts} shown.
							</p>
						{/if}
					</div>
				{/each}
			</div>
		</Popover.Content>
	</Popover.Root>
{/if}
