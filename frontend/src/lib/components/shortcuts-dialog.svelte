<script lang="ts" module>
	export type Shortcut = [keys: string, label: string];
</script>

<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import { Kbd } from '$lib/components/ui/kbd';
	import { MOD_KEY } from '$lib/utils';

	interface Props {
		open: boolean;
		shortcuts: Shortcut[];
		title?: string;
	}

	let { open = $bindable(false), shortcuts, title = 'On this page' }: Props = $props();

	const GLOBAL: Shortcut[] = [
		[`${MOD_KEY}+K`, 'Search and commands'],
		[`${MOD_KEY}+Shift+K`, 'Toolbox'],
		[`${MOD_KEY}+B`, 'Show or hide the sidebar']
	];
</script>

{#snippet list(heading: string, rows: Shortcut[])}
	<section class="flex flex-col gap-2">
		<h3 class="text-2xs font-semibold tracking-wide text-muted-foreground uppercase">{heading}</h3>
		<dl class="grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-2 text-sm">
			{#each rows as [keys, label] (keys)}
				<dt><Kbd>{keys}</Kbd></dt>
				<dd class="text-muted-foreground">{label}</dd>
			{/each}
		</dl>
	</section>
{/snippet}

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header><Dialog.Title>Keyboard shortcuts</Dialog.Title></Dialog.Header>
		<div class="flex flex-col gap-5">
			{@render list(title, [...shortcuts, ['?', 'Show these shortcuts']])}
			{@render list('Everywhere', GLOBAL)}
		</div>
	</Dialog.Content>
</Dialog.Root>
