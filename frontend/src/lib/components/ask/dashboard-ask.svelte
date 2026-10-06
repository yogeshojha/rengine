<script lang="ts">
	import { goto } from '$app/navigation';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import { estateApi } from '$lib/api/ask';
	import { ROUTES } from '$lib/config/routes';
	import { scopeToParams } from '$lib/utilities/dashboard-scope';
	import { morph } from '$lib/utilities/view-transition';
	import type { TargetScope } from '$lib/utilities/surface-scope';

	interface Props {
		scope: TargetScope;
	}

	let { scope }: Props = $props();

	let available = $state(false);

	$effect(() => {
		void estateApi
			.status()
			.then((s) => (available = s.available))
			.catch(() => (available = false));
	});

	function open() {
		void morph(() => goto(ROUTES.ask({ scope: scopeToParams(new URLSearchParams(), scope) })));
	}
</script>

{#if available}
	<button
		type="button"
		class="ask-composer flex h-8 w-full max-w-md items-center gap-2 rounded-lg border bg-card px-2.5 text-left text-sm text-muted-foreground hover:border-ring/50"
		onclick={open}
	>
		<Sparkles class="size-3.5 shrink-0 text-primary" />
		Ask a question
	</button>
{/if}
