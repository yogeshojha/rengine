<script lang="ts">
	import { getInitials } from '$lib/utilities/strings';

	interface Props {
		name: string;
		picture: string | null | undefined;
	}

	let { name, picture }: Props = $props();
</script>

<span
	class="flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-md border bg-muted/50 text-2xs font-semibold text-muted-foreground"
>
	{#if picture}
		<img src={picture} alt="" class="size-full object-cover" loading="lazy" />
	{:else}
		{getInitials(name)}
	{/if}
</span>
