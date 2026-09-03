<script lang="ts">
	interface Props {
		code: string | null | undefined;
		showCode?: boolean;
		class?: string;
	}

	let { code, showCode = true, class: className = '' }: Props = $props();

	let iso = $derived((code ?? '').trim().toLowerCase());
	let valid = $derived(/^[a-z]{2}$/.test(iso));
</script>

{#if valid}
	<span class="inline-flex items-center gap-1.5 {className}">
		<span class="fi fi-{iso} shrink-0 rounded-[2px] leading-none" aria-hidden="true"></span>
		{#if showCode}<span class="uppercase">{iso}</span>{/if}
		<span class="sr-only">{iso.toUpperCase()}</span>
	</span>
{:else}
	<span class="text-muted-foreground {className}">—</span>
{/if}
