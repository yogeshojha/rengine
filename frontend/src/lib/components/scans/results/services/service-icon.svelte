<script lang="ts">
	import TechIcon from '../tech-icon.svelte';
	import { SERVICE_CLASS_ICONS } from '$lib/config/service-classes';
	import Server from '@lucide/svelte/icons/server';

	interface Props {
		service: string | null;
		serviceClass: string;
		product?: string | null;
		class?: string;
	}

	let { service, serviceClass, product = null, class: className = 'size-4' }: Props = $props();

	// the brand mark when the service is a product, the class glyph when it is a protocol
	let name = $derived(product?.split(/[\s/_(,-]/)[0] || service || '');
	let ClassIcon = $derived(SERVICE_CLASS_ICONS[serviceClass] ?? Server);
</script>

{#if name}
	<TechIcon {name} class={className}>
		{#snippet fallback()}
			<ClassIcon class="{className} text-muted-foreground" />
		{/snippet}
	</TechIcon>
{:else}
	<ClassIcon class="{className} text-muted-foreground" />
{/if}
