import { toast } from 'svelte-sonner';
import { connectorsApi } from '$lib/api/connectors';
import { ACTION_KIND_LABELS, ONLINE_STATES, type ActionKind } from '$lib/config/connectors';
import { proxyTool } from '$lib/stores/proxy-tool.svelte';
import type { Connector, ConnectorSpec, HandoffRequest, HandoffResult } from '$lib/types/connector';

export function proxyLabel(connector: Connector, catalog: ConnectorSpec[]): string {
	return catalog.find((c) => c.kind === connector.kind)?.title ?? connector.name;
}

/** The proxy's short name, as in Burp Repeater. */
export function proxyName(connector: Connector, catalog: ConnectorSpec[]): string {
	return catalog.find((c) => c.kind === connector.kind)?.short_title ?? connector.name;
}

function requests(count: number | null): string {
	if (count === null) return 'The requests';
	if (count === 1) return 'The request';
	return `${count.toLocaleString()} requests`;
}

/** Asks before a send to the proxy unless the user turned the question off. */
export function confirmSend(
	connector: Connector,
	catalog: ConnectorSpec[],
	kind: ActionKind,
	count: number | null = 1
): Promise<boolean> {
	const proxy = proxyLabel(connector, catalog);
	const tool = ACTION_KIND_LABELS[kind];
	const noun = requests(count);
	let description = `${noun} will be sent to ${tool}.`;
	if (connector.state === 'paused') {
		description = `The ${proxy} connection is paused. ${noun} will be delivered to ${tool} when the connection is resumed.`;
	} else if (!ONLINE_STATES.has(connector.state)) {
		description = `${proxy} is not connected. ${noun} will be delivered to ${tool} when the extension connects.`;
	}
	return proxyTool.confirm(`Send to ${proxy}`, description);
}

interface HandoffCall {
	connectorId: string;
	projectId: string;
	scanId?: string | null;
	body: HandoffRequest;
	connectors: Connector[];
	catalog: ConnectorSpec[];
}

/** Queues the rows for the proxy and reports what was queued. */
export async function handoffToProxy(call: HandoffCall): Promise<HandoffResult | null> {
	const connector = call.connectors.find((c) => c.id === call.connectorId);
	const proxy = connector ? proxyLabel(connector, call.catalog) : 'the proxy';
	try {
		const res = await connectorsApi.handoff(
			call.connectorId,
			call.projectId,
			call.body,
			call.scanId
		);
		const noun = res.queued === 1 ? 'request' : 'requests';
		const skipped = res.skipped ? ` ${res.skipped.toLocaleString()} skipped.` : '';
		if (!res.queued) {
			toast.error(`No request sent.${skipped}`);
			return null;
		}
		if (res.online) {
			toast.success(`${res.queued.toLocaleString()} ${noun} sent to ${res.tool}.${skipped}`);
		} else {
			toast.warning(
				`${res.queued.toLocaleString()} ${noun} queued. ${proxy} is offline.${skipped}`
			);
		}
		return res;
	} catch (e) {
		toast.error(e instanceof Error ? e.message : 'Requests not sent');
		return null;
	}
}
