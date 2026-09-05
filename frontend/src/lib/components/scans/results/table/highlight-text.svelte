<script lang="ts">
	interface Props {
		text: string;
		term?: string;
		terms?: string[];
	}

	let { text, term = '', terms }: Props = $props();

	let needles = $derived(
		(terms ?? [term]).map((t) => t.trim().toLowerCase()).filter((t) => t.length > 0)
	);

	let parts = $derived.by(() => {
		if (!needles.length) return [{ text, hit: false }];
		const out: { text: string; hit: boolean }[] = [];
		const haystack = text.toLowerCase();
		let from = 0;
		for (;;) {
			let at = -1;
			let len = 0;
			for (const needle of needles) {
				const i = haystack.indexOf(needle, from);
				if (i !== -1 && (at === -1 || i < at || (i === at && needle.length > len))) {
					at = i;
					len = needle.length;
				}
			}
			if (at === -1) break;
			if (at > from) out.push({ text: text.slice(from, at), hit: false });
			out.push({ text: text.slice(at, at + len), hit: true });
			from = at + len;
		}
		if (from < text.length) out.push({ text: text.slice(from), hit: false });
		return out;
	});
</script>

{#each parts as part, i (i)}{#if part.hit}<mark class="rounded-xs bg-primary/20 text-foreground"
			>{part.text}</mark
		>{:else}{part.text}{/if}{/each}
