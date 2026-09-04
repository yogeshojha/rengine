<script lang="ts">
	import CheckCheck from '@lucide/svelte/icons/check-check';
	import { Badge } from '$lib/components/ui/badge';
	import Hint from '$lib/components/hint.svelte';
	import { CORROBORATION_BASIS_LABELS } from '$lib/config/vulnerabilities';
	import type { Corroboration } from '$lib/utilities/vulns';

	interface Props {
		peers: Corroboration[];
		scanner: string;
		onFilter?: (token: string) => void;
	}

	let { peers, scanner, onFilter }: Props = $props();

	const MAX_NAMED = 3;

	let hint = $derived.by(() => {
		if (peers.length === 1) {
			const basis = CORROBORATION_BASIS_LABELS[peers[0].basis];
			return `Also reported by ${peers[0].template_name}${basis ? `. ${basis}` : ''}`;
		}
		const named = peers.slice(0, MAX_NAMED).map((p) => p.template_name);
		const rest = peers.length - named.length;
		const tail = rest > 0 ? ` and ${rest} more` : '';
		return `Also reported by ${peers.length} other checks: ${named.join(', ')}${tail}`;
	});

	let crossScanner = $derived(peers.some((p) => p.scanner !== scanner));
	let text = $derived(crossScanner ? `${hint}. Another scanner found it too` : hint);
</script>

{#if peers.length}
	<Hint {text}>
		{#snippet child(props)}
			{#if onFilter}
				<button
					{...props}
					type="button"
					class="flex h-5 shrink-0 items-center"
					onclick={(e) => {
						e.stopPropagation();
						onFilter('is:corroborated');
					}}
				>
					<Badge variant="secondary" class="gap-1 px-1 text-[10px] font-normal">
						<CheckCheck class="size-2.5" /> confirmed
					</Badge>
				</button>
			{:else}
				<span {...props} class="flex h-4 shrink-0 items-center">
					<Badge variant="secondary" class="gap-1 px-1 text-[10px] font-normal">
						<CheckCheck class="size-2.5" /> confirmed
					</Badge>
				</span>
			{/if}
		{/snippet}
	</Hint>
{/if}
