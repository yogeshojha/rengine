// mirrors shared/utils/net.py
export function bracketed(host: string): string {
	return host.includes(':') && !host.startsWith('[') ? `[${host}]` : host;
}

export function hostPort(host: string, port: number | string): string {
	return `${bracketed(host)}:${port}`;
}
