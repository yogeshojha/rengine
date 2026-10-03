<script lang="ts">
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import BrandMark from '$lib/components/icons/brand-mark.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { PRODUCT_NAME } from '$lib/constants';
	import { pageTitle } from '$lib/utilities/page-title';

	const NOT_FOUND = 404;

	let missing = $derived(page.status === NOT_FOUND);
	let title = $derived(missing ? 'Page not found' : 'Page not loaded');
	let description = $derived(
		missing
			? 'No page at this address.'
			: 'Reload the page. If it fails again, check that the api service is running.'
	);
</script>

<svelte:head><title>{pageTitle(title)}</title></svelte:head>

<div class="flex min-h-svh flex-col items-center justify-center gap-6 bg-muted p-6 md:p-10">
	<div class="flex w-full max-w-sm flex-col gap-6">
		<a
			href={ROUTES.dashboard}
			class="flex items-center gap-2 self-center font-medium text-foreground"
		>
			<BrandMark />
			{PRODUCT_NAME}
		</a>
		<Card.Root>
			<Card.Header class="text-center">
				<p class="font-mono text-sm text-muted-foreground tabular-nums">{page.status}</p>
				<Card.Title class="text-xl">{title}</Card.Title>
				<Card.Description>{description}</Card.Description>
			</Card.Header>
			<Card.Content class="flex justify-center gap-2">
				{#if !missing}
					<Button variant="outline" onclick={() => window.location.reload()}>Reload</Button>
				{/if}
				<Button href={ROUTES.dashboard}>Open dashboard</Button>
			</Card.Content>
		</Card.Root>
	</div>
</div>
