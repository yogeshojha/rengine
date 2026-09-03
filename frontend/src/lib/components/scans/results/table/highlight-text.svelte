<script lang="ts">
	interface Props {
		text: string;
		term: string;
	}

	let { text, term }: Props = $props();

	let parts = $derived.by(() => {
		const needle = term.trim().toLowerCase();
		if (!needle) return [{ text, hit: false }];
		const out: { text: string; hit: boolean }[] = [];
		const haystack = text.toLowerCase();
		let from = 0;
		let at = haystack.indexOf(needle);
		while (at !== -1) {
			if (at > from) out.push({ text: text.slice(from, at), hit: false });
			out.push({ text: text.slice(at, at + needle.length), hit: true });
			from = at + needle.length;
			at = haystack.indexOf(needle, from);
		}
		if (from < text.length) out.push({ text: text.slice(from), hit: false });
		return out;
	});
</script>

{#each parts as part, i (i)}{#if part.hit}<mark class="rounded-xs bg-primary/20 text-foreground"
			>{part.text}</mark
		>{:else}{part.text}{/if}{/each}
