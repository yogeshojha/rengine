<script lang="ts">
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import CountryFlag from '$lib/components/scans/results/country-flag.svelte';
	import { nameserverProvider, registrarIcon } from '$lib/config/dns-providers';
	import { glyphIcon } from '$lib/config/toolbox';
	import type { Identity } from '$lib/types/toolbox';

	let { identity, class: className = 'size-4' }: { identity: Identity; class?: string } = $props();

	const provider = $derived(
		identity.kind === 'nameserver' ? nameserverProvider([identity.value]) : null
	);
	const techName = $derived.by(() => {
		if (identity.kind === 'tech') return registrarIcon(identity.value) ?? identity.value;
		if (identity.kind === 'nameserver') return provider?.icon ?? null;
		return null;
	});
	const Glyph = $derived(identity.kind === 'glyph' ? glyphIcon(identity.value) : null);
</script>

{#if identity.kind === 'flag'}
	<CountryFlag
		code={identity.value}
		showCode={false}
		class="shrink-0 [&_.fi]:size-full {className}"
	/>
{:else if identity.kind === 'favicon'}
	<img src={identity.value} alt="" aria-hidden="true" class="shrink-0 object-contain {className}" />
{:else if Glyph}
	<Glyph class="shrink-0 {className}" />
{:else if techName}
	<TechIcon name={techName} class={className} />
{/if}
