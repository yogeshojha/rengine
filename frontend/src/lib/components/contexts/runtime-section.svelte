<script lang="ts">
	import { Label } from '$lib/components/ui/label';
	import * as Select from '$lib/components/ui/select';
	import {
		HTTP_PROTOCOLS,
		type ScanContextRead,
		type ScanContextCreate,
		type HttpProtocol
	} from '$lib/types/scan-context';
	import { HTTP_PROTOCOL_LABELS } from './context-summary';

	type CtxLike = ScanContextRead | ScanContextCreate;

	interface Props {
		context: CtxLike;
		onChange: (updates: Partial<CtxLike>) => void;
	}

	let { context, onChange }: Props = $props();

	const PROTOCOL_OPTS = HTTP_PROTOCOLS.map((value) => ({
		value,
		label: HTTP_PROTOCOL_LABELS[value]
	}));

	const REDIRECT_OPTS = [
		{ value: 'null', label: 'Engine default' },
		{ value: 'true', label: 'Follow' },
		{ value: 'false', label: 'Do not follow' }
	];

	let redirectValue = $derived(
		context.follow_redirects_override == null ? 'null' : String(context.follow_redirects_override)
	);

	function setProtocol(v: string | undefined) {
		onChange({ http_protocol: (v ?? 'both') as HttpProtocol });
	}

	function setRedirect(v: string | undefined) {
		const next = v === 'true' ? true : v === 'false' ? false : null;
		onChange({ follow_redirects_override: next });
	}
</script>

<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
	<div class="space-y-1.5">
		<Label class="text-xs">HTTP protocol</Label>
		<Select.Root type="single" value={context.http_protocol} onValueChange={setProtocol}>
			<Select.Trigger class="h-9 w-full text-sm">
				{HTTP_PROTOCOL_LABELS[context.http_protocol] ?? HTTP_PROTOCOL_LABELS.both}
			</Select.Trigger>
			<Select.Content>
				{#each PROTOCOL_OPTS as opt (opt.value)}
					<Select.Item value={opt.value} label={opt.label}>{opt.label}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
	</div>

	<div class="space-y-1.5">
		<Label class="text-xs">Follow redirects</Label>
		<Select.Root type="single" value={redirectValue} onValueChange={setRedirect}>
			<Select.Trigger class="h-9 w-full text-sm">
				{REDIRECT_OPTS.find((o) => o.value === redirectValue)?.label ?? 'Engine default'}
			</Select.Trigger>
			<Select.Content>
				{#each REDIRECT_OPTS as opt (opt.value)}
					<Select.Item value={opt.value} label={opt.label}>{opt.label}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
	</div>
</div>
