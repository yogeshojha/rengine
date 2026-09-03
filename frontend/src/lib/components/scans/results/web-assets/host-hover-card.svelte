<script lang="ts">
	import type { Snippet } from 'svelte';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { Badge } from '$lib/components/ui/badge';
	import TechIcon from '../tech-icon.svelte';
	import { screenshotUrl } from '$lib/utilities/media';
	import { providerFor, PROVIDER_KIND_ICONS } from '$lib/config/hosting-providers';
	import { httpStatusClass, httpStatusReason, STATUS_DOT } from '$lib/utilities/scan-correlation';
	import type { SubdomainRead } from '$lib/types/subdomain';

	interface Props {
		sub: SubdomainRead;
		children: Snippet;
	}

	let { sub, children }: Props = $props();

	const MAX_IPS = 3;
	const MAX_TECH = 4;

	let failed = $state(false);
	let url = $derived(failed ? null : screenshotUrl(sub.screenshot_path));
	let rich = $derived(!!(sub.http_status || sub.resolved_ips?.length || sub.cname));
	let redirected = $derived(!!sub.final_url && sub.final_url !== sub.http_url);
	let provider = $derived(providerFor(sub.cname));
	let ProviderIcon = $derived(provider ? PROVIDER_KIND_ICONS[provider.kind] : null);
</script>

{#if rich}
	<HoverCard.Root openDelay={320} closeDelay={80}>
		<HoverCard.Trigger>
			{#snippet child({ props })}
				<span {...props}>{@render children()}</span>
			{/snippet}
		</HoverCard.Trigger>
		<HoverCard.Content side="right" align="start" class="w-80 overflow-hidden p-0">
			{#if url}
				<img
					src={url}
					alt="Screenshot of {sub.name}"
					loading="lazy"
					onerror={() => (failed = true)}
					class="aspect-video w-full border-b border-border bg-muted object-cover object-top"
				/>
			{/if}
			<div class="flex flex-col gap-2 p-3 text-xs">
				<div class="flex items-center gap-2">
					<span class="size-2 rounded-full {STATUS_DOT[httpStatusClass(sub.http_status)]}"></span>
					<span class="font-mono font-medium">{sub.http_status ?? 'No HTTP'}</span>
					<span class="text-muted-foreground">{httpStatusReason(sub.http_status)}</span>
				</div>
				{#if sub.page_title}
					<p class="line-clamp-2 text-sm leading-snug">{sub.page_title}</p>
				{/if}
				{#if redirected}
					<p class="truncate font-mono text-muted-foreground">→ {sub.final_url}</p>
				{/if}
				{#if sub.resolved_ips?.length}
					<p class="font-mono text-muted-foreground">
						{sub.resolved_ips.slice(0, MAX_IPS).join(' · ')}{sub.resolved_ips.length > MAX_IPS
							? ` · +${sub.resolved_ips.length - MAX_IPS}`
							: ''}
					</p>
				{:else if sub.cname}
					<p class="flex items-center gap-1 truncate font-mono text-muted-foreground">
						{#if provider && ProviderIcon}
							<ProviderIcon class="size-3 shrink-0" />
							<span class="shrink-0 font-sans">{provider.label} ·</span>
						{/if}
						<span class="truncate">{sub.cname}</span>
					</p>
				{/if}
				{#if sub.resolved_ips?.length && provider && ProviderIcon}
					<p class="flex items-center gap-1 text-muted-foreground">
						<ProviderIcon class="size-3 shrink-0" />
						<span>{provider.label}</span>
						<span class="truncate font-mono">· {sub.cname}</span>
					</p>
				{/if}
				{#if (sub.title_count ?? 0) > 1}
					<p class="text-muted-foreground">Same page on {(sub.title_count ?? 0) - 1} other hosts</p>
				{/if}
				{#if sub.tech.length}
					<div class="flex flex-wrap gap-1">
						{#each sub.tech.slice(0, MAX_TECH) as t (t)}
							<Badge variant="outline" class="font-normal">
								<TechIcon name={t} />
								{t}
							</Badge>
						{/each}
						{#if sub.tech.length > MAX_TECH}
							<Badge variant="outline" class="font-normal text-muted-foreground">
								+{sub.tech.length - MAX_TECH}
							</Badge>
						{/if}
					</div>
				{/if}
			</div>
		</HoverCard.Content>
	</HoverCard.Root>
{:else}
	{@render children()}
{/if}
