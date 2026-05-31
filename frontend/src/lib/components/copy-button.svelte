<script lang="ts">
	import { Check, Copy, X } from 'lucide-svelte';
	import { Button } from '$lib/components/ui/button';
	import * as Tooltip from '$lib/components/ui/tooltip';

	interface Props {
		value: string;
		class?: string;
	}

	let { value, class: className = '' }: Props = $props();

	let copied = $state(false);
	let failed = $state(false);

	async function writeClipboard(text: string): Promise<boolean> {
		if (navigator.clipboard && window.isSecureContext) {
			try {
				await navigator.clipboard.writeText(text);
				return true;
			} catch {
				// fall through to legacy path
			}
		}
		// Fallback for non-secure contexts (e.g. http://<lan-ip>:5173)
		try {
			const ta = document.createElement('textarea');
			ta.value = text;
			ta.style.position = 'fixed';
			ta.style.opacity = '0';
			document.body.appendChild(ta);
			ta.focus();
			ta.select();
			const ok = document.execCommand('copy');
			ta.remove();
			return ok;
		} catch {
			return false;
		}
	}

	async function copy(e?: MouseEvent) {
		e?.stopPropagation();
		if (await writeClipboard(value)) {
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} else {
			failed = true;
			setTimeout(() => (failed = false), 2000);
		}
	}
</script>

<Tooltip.Root ignoreNonKeyboardFocus>
	<Tooltip.Trigger>
		{#snippet child({ props })}
			<Button
				{...props}
				variant="ghost"
				size="icon"
				class="h-7 w-7 shrink-0 {className}"
				onclick={(e) => copy(e)}
			>
				{#if copied}
					<Check class="h-3.5 w-3.5 text-green-500" />
				{:else if failed}
					<X class="h-3.5 w-3.5 text-destructive" />
				{:else}
					<Copy class="h-3.5 w-3.5 text-muted-foreground" />
				{/if}
			</Button>
		{/snippet}
	</Tooltip.Trigger>

	<Tooltip.Content>
		<p>{copied ? 'Copied!' : failed ? 'Failed to copy' : 'Copy'}</p>
	</Tooltip.Content>
</Tooltip.Root>
