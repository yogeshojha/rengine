<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Copy from '@lucide/svelte/icons/copy';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import BrandMark from '$lib/components/icons/brand-mark.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import { aboutApi } from '$lib/api/about';
	import { NO_RESPONSE } from '$lib/api/client';
	import { aboutDetails, checkCount, modeLabel, NOT_AVAILABLE } from '$lib/utilities/about-details';
	import { relativeTimeLong } from '$lib/utilities/dates';
	import { externalHref } from '$lib/utilities/links';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import type { About } from '$lib/types/about';

	let { open = $bindable(false) }: { open: boolean } = $props();

	let about = $state<About | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			about = await aboutApi.get();
		} catch (e) {
			error = e instanceof Error && e.message ? e.message : NO_RESPONSE;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (open) untrack(() => void load());
	});

	const library = $derived.by(() => {
		const found = about?.check_library;
		if (!found) return null;
		const synced = found.synced_at ? `Synced ${relativeTimeLong(found.synced_at)}` : null;
		return [checkCount(found), synced].filter(Boolean).join(' · ') || null;
	});

	const rows = $derived(
		about
			? [
					{ label: 'Mode', value: modeLabel(about.mode), mono: false },
					{ label: 'Architecture', value: about.architecture, mono: true },
					{ label: 'PostgreSQL', value: about.postgres, mono: true },
					{ label: 'Redis', value: about.redis, mono: true },
					{ label: 'Check library', value: library, mono: false }
				]
			: []
	);

	async function copy() {
		if (!about) return;
		if (await writeClipboard(aboutDetails(about))) toast.success('Details copied');
		else toast.error('Details not copied');
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="gap-0 p-0 sm:max-w-xl">
		<Dialog.Header class="border-b px-6 py-4">
			<Dialog.Title>About reNgine</Dialog.Title>
		</Dialog.Header>

		<ScrollArea class="min-h-0 [&_[data-slot=scroll-area-viewport]]:max-h-[calc(100dvh-12rem)]">
			<div class="flex min-w-0 flex-col gap-5 px-6 py-5">
				<div class="flex items-center gap-3">
					<BrandMark class="size-10" />
					<div class="flex min-w-0 flex-col gap-0.5">
						{#if about}
							<span class="text-base leading-6 font-semibold">reNgine {about.version}</span>
							<span class="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
								<span>GPL-3.0</span>
								{#if externalHref(about.release_url)}
									<span aria-hidden="true">·</span>
									<a
										href={externalHref(about.release_url)}
										target="_blank"
										rel="noopener noreferrer"
										class="inline-flex items-center gap-1 hover:text-foreground"
									>
										Release notes
										<ExternalLink class="size-3" aria-hidden="true" />
									</a>
								{/if}
							</span>
						{:else if loading}
							<Skeleton class="h-5 w-32" />
							<Skeleton class="h-4 w-40" />
						{:else}
							<span class="text-base leading-6 font-semibold">reNgine</span>
						{/if}
					</div>
				</div>

				{#if error}
					<div class="flex items-center justify-between gap-4 rounded-md border px-3 py-2.5">
						<p class="text-sm text-destructive" role="alert">{error}</p>
						<Button variant="outline" size="sm" onclick={() => load()}>Retry</Button>
					</div>
				{:else}
					<section class="flex flex-col gap-2.5">
						<SectionHead title="Instance" />
						<dl class="grid grid-cols-2 gap-x-6 gap-y-3">
							{#if about}
								{#each rows as row (row.label)}
									<div class="flex min-w-0 flex-col gap-0.5">
										<dt class="text-xs text-muted-foreground">{row.label}</dt>
										<dd
											class="text-sm leading-5 break-words {row.value
												? row.mono
													? 'font-mono'
													: ''
												: 'text-muted-foreground'}"
										>
											{row.value ?? NOT_AVAILABLE}
										</dd>
									</div>
								{/each}
							{:else}
								{#each Array(5) as _, i (i)}
									<div class="flex flex-col gap-1">
										<Skeleton class="h-3.5 w-20" />
										<Skeleton class="h-5 w-28" />
									</div>
								{/each}
							{/if}
						</dl>
					</section>

					<section class="flex min-w-0 flex-col gap-2.5">
						<SectionHead title="Tools" count={about?.tools.length ?? null} />
						<div class="rounded-md border">
							<ScrollArea class="h-[min(15rem,28dvh)]">
								<ul class="grid grid-cols-1 gap-x-8 px-3 py-1.5 sm:grid-cols-2">
									{#if about}
										{#each about.tools as tool (tool.name)}
											<li class="flex min-w-0 items-baseline justify-between gap-3 py-1">
												<span class="truncate text-sm">{tool.name}</span>
												<a
													href={externalHref(tool.url)}
													target="_blank"
													rel="noopener noreferrer"
													class="shrink-0 font-mono text-xs text-muted-foreground hover:text-foreground"
												>
													{tool.version}
												</a>
											</li>
										{/each}
									{:else}
										{#each Array(10) as _, i (i)}
											<li class="flex items-center justify-between gap-3 py-1.5">
												<Skeleton class="h-4 w-24" />
												<Skeleton class="h-4 w-14" />
											</li>
										{/each}
									{/if}
								</ul>
							</ScrollArea>
						</div>
					</section>
				{/if}
			</div>
		</ScrollArea>

		<Dialog.Footer class="border-t px-6 py-4 sm:items-center sm:justify-between">
			<div class="flex items-center justify-center gap-4 text-sm">
				{#if about}
					<a
						href={externalHref(about.documentation_url)}
						target="_blank"
						rel="noopener noreferrer"
						class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
					>
						Documentation
						<ExternalLink class="size-3.5" aria-hidden="true" />
					</a>
					<a
						href={externalHref(about.issue_url)}
						target="_blank"
						rel="noopener noreferrer"
						class="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
					>
						Report an issue
						<ExternalLink class="size-3.5" aria-hidden="true" />
					</a>
				{/if}
			</div>
			<Button class="w-full sm:w-auto" disabled={!about} onclick={() => copy()}>
				<Copy class="size-4" />
				Copy details
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
