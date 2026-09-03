<script lang="ts">
	import Waypoints from '@lucide/svelte/icons/waypoints';
	import Plus from '@lucide/svelte/icons/plus';
	import Check from '@lucide/svelte/icons/check';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import { toast } from 'svelte-sonner';
	import * as Card from '$lib/components/ui/card';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import { Badge } from '$lib/components/ui/badge';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { targetsApi } from '$lib/api/targets';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import type { RelatedDomain, RelatedDomains } from '$lib/types/asset-query';

	interface Props {
		set: RelatedDomains | null;
	}

	let { set }: Props = $props();

	let added = new SvelteSet<string>();
	let pending = $state<string | null>(null);

	let domains = $derived(set?.domains ?? []);

	async function addTarget(domain: RelatedDomain) {
		const slug = projectsStore.activeProject?.slug;
		if (!slug) return;
		pending = domain.domain;
		try {
			await targetsApi.create({ target_value: domain.domain, project_slug: slug });
			added.add(domain.domain);
			toast.success(`${domain.domain} added as a target`);
		} catch {
			toast.error(`Could not add ${domain.domain}`);
		} finally {
			pending = null;
		}
	}
</script>

{#if domains.length}
	<Card.Root class="gap-0 py-0">
		<Card.Header class="gap-1 border-b p-4">
			<Card.Title class="flex items-center gap-2 text-sm">
				<Waypoints class="size-4 text-primary" />
				Related domains
				<Badge variant="secondary" class="ml-auto tabular-nums">{domains.length}</Badge>
			</Card.Title>
			<Card.Description class="text-xs">
				Domains outside {set?.root} that this scan links to it. Add one as a target to bring it in scope.
			</Card.Description>
		</Card.Header>
		<div class="divide-y divide-border/60">
			{#each domains as domain (domain.domain)}
				{@const done = domain.is_target || added.has(domain.domain)}
				<Collapsible.Root class="px-4 py-3">
					<div class="flex items-start justify-between gap-3">
						<div class="min-w-0">
							<div class="truncate font-mono text-sm font-medium">{domain.domain}</div>
							<div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
								<Badge variant="outline" class="gap-1 text-[10px] font-normal">
									<ShieldCheck class="size-3" />
									{domain.reason_label}
								</Badge>
								<Collapsible.Trigger
									class="text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
								>
									{domain.hostname_count}
									{domain.hostname_count === 1 ? 'hostname' : 'hostnames'}
								</Collapsible.Trigger>
							</div>
						</div>
						{#if done}
							<Badge variant="success" class="shrink-0 gap-1">
								<Check class="size-3" />
								Target
							</Badge>
						{:else}
							<LoadingButton
								size="sm"
								variant="outline"
								class="h-8 shrink-0 gap-1.5"
								loading={pending === domain.domain}
								onclick={() => addTarget(domain)}
							>
								<Plus class="size-3.5" />
								Add target
							</LoadingButton>
						{/if}
					</div>
					<Collapsible.Content>
						<p class="mt-2.5 text-xs text-muted-foreground">{domain.reason_detail}</p>
						<ul class="mt-2 space-y-1 border-l pl-3">
							{#each domain.evidence as item (item.hostname)}
								<li class="min-w-0 text-xs">
									<span class="block truncate font-mono text-foreground">{item.hostname}</span>
									<span class="block truncate text-muted-foreground">found via {item.seen_on}</span>
								</li>
							{/each}
							{#if domain.hostname_count > domain.evidence.length}
								<li class="text-xs text-muted-foreground">
									and {domain.hostname_count - domain.evidence.length} more
								</li>
							{/if}
						</ul>
					</Collapsible.Content>
				</Collapsible.Root>
			{/each}
		</div>
	</Card.Root>
{/if}
