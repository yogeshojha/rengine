import { toast } from 'svelte-sonner';
import { connectorsApi } from '$lib/api/connectors';
import type { Connector, ConnectorSpec, HandoffRequest, HandoffResult } from '$lib/types/connector';

export function proxyLabel(connector: Connector, catalog: ConnectorSpec[]): string {
	return catalog.find((c) => c.kind === connector.kind)?.title ?? connector.name;
}

/** The proxy's short name, as in Burp Repeater. */
export function proxyName(connector: Connector, catalog: ConnectorSpec[]): string {
	return catalog.find((c) => c.kind === connector.kind)?.short_title ?? connector.name;
}

interface HandoffCall {
	connectorId: string;
	projectId: string;
	scanId?: string | null;
	body: HandoffRequest;
	connectors: Connector[];
	catalog: ConnectorSpec[];
}

type PreviewCall = Pick<HandoffCall, 'connectorId' | 'projectId' | 'scanId' | 'body'>;

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

/** The raw request a hand-off of one row sends, or null when there is none. */
export async function previewHandoff(call: PreviewCall): Promise<string | null> {
	try {
		const res = await connectorsApi.preview(
			call.connectorId,
			call.projectId,
			call.body,
			call.scanId
		);
		return res.request;
	} catch (e) {
		toast.error(e instanceof Error ? e.message : 'Request not loaded');
		return null;
	}
}
