#!/usr/bin/env node
// Production entry of the frontend image: the adapter-node build, with /api forwarded to the
// api service the way the vite dev proxy forwards it (vite.config.ts), event streams included.
import http from 'node:http';
import https from 'node:https';

const API_ORIGIN = new URL(process.env.API_ORIGIN ?? 'http://api:8000');
const HOST = process.env.HOST ?? '0.0.0.0';
const PORT = Number(process.env.PORT ?? 3000);

const { handler } = await import(new URL('../build/handler.js', import.meta.url).href);
const client = API_ORIGIN.protocol === 'https:' ? https : http;

function forward(req, res) {
	const upstream = client.request(
		{
			protocol: API_ORIGIN.protocol,
			hostname: API_ORIGIN.hostname,
			port: API_ORIGIN.port,
			method: req.method,
			path: req.url,
			headers: { ...req.headers, host: API_ORIGIN.host }
		},
		(reply) => {
			res.writeHead(reply.statusCode ?? 502, reply.headers);
			if (reply.headers['content-type']?.includes('text/event-stream')) res.flushHeaders();
			reply.pipe(res);
			// an api that drops mid-response (a restart during an event stream) never ends the pipe;
			// cutting the client connection lets the browser see the break and reconnect
			reply.on('close', () => {
				if (!reply.complete) res.destroy();
			});
		}
	);
	upstream.on('error', () => {
		// once the reply has started, a 502 body would corrupt it; the connection is cut instead
		if (res.headersSent) return res.destroy();
		res.writeHead(502, { 'content-type': 'text/plain' });
		res.end('The api is unreachable.');
	});
	// a browser that leaves mid-response (an event stream, say) ends the upstream request with it
	res.on('close', () => {
		if (!res.writableFinished) upstream.destroy();
	});
	req.pipe(upstream);
}

const server = http.createServer((req, res) => {
	if (req.url?.startsWith('/api')) forward(req, res);
	else handler(req, res);
});

server.listen(PORT, HOST, () => {
	console.log(`Listening on http://${HOST}:${PORT}, /api forwarded to ${API_ORIGIN.origin}`);
});

for (const signal of ['SIGINT', 'SIGTERM']) {
	process.on(signal, () => {
		server.close(() => process.exit(0));
		// open event streams would otherwise hold the close until the container is killed
		server.closeAllConnections();
	});
}
