import type { PDFDocumentProxy, PDFPageProxy, RenderTask } from 'pdfjs-dist';

const MAX_DPR = 2;

type Pdfjs = typeof import('pdfjs-dist');

let library: Promise<Pdfjs> | null = null;

function pdfjs(): Promise<Pdfjs> {
	library ??= (async () => {
		const [lib, worker] = await Promise.all([
			import('pdfjs-dist'),
			import('pdfjs-dist/build/pdf.worker.min.mjs?url')
		]);
		lib.GlobalWorkerOptions.workerSrc = worker.default;
		return lib;
	})();
	return library;
}

export interface PageSize {
	width: number;
	height: number;
}

export interface OutlineEntry {
	title: string;
	depth: number;
	page: number | null;
}

export async function loadDocument(data: ArrayBuffer): Promise<PDFDocumentProxy> {
	const lib = await pdfjs();
	return lib.getDocument({ data }).promise;
}

export async function pageSizes(doc: PDFDocumentProxy): Promise<PageSize[]> {
	const pages = await Promise.all(
		Array.from({ length: doc.numPages }, (_, i) => doc.getPage(i + 1))
	);
	return pages.map((page) => {
		const { width, height } = page.getViewport({ scale: 1 });
		return { width, height };
	});
}

export function renderPage(
	page: PDFPageProxy,
	canvas: HTMLCanvasElement,
	scale: number
): RenderTask {
	const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR);
	const viewport = page.getViewport({ scale: scale * dpr });
	canvas.width = Math.round(viewport.width);
	canvas.height = Math.round(viewport.height);
	canvas.style.width = `${Math.round(viewport.width / dpr)}px`;
	canvas.style.height = `${Math.round(viewport.height / dpr)}px`;
	return page.render({ canvas, viewport });
}

export function releaseCanvas(canvas: HTMLCanvasElement): void {
	canvas.width = 0;
	canvas.height = 0;
}

export async function readOutline(doc: PDFDocumentProxy): Promise<OutlineEntry[]> {
	const raw = await doc.getOutline().catch(() => null);
	if (!raw?.length) return [];

	const entries: OutlineEntry[] = [];
	const walk = async (items: typeof raw, depth: number) => {
		for (const item of items) {
			entries.push({
				title: item.title?.trim() || 'Untitled',
				depth,
				page: await destinationPage(doc, item.dest)
			});
			if (item.items?.length && depth < 1) await walk(item.items, depth + 1);
		}
	};
	await walk(raw, 0);
	return entries;
}

async function destinationPage(doc: PDFDocumentProxy, dest: unknown): Promise<number | null> {
	try {
		const resolved = typeof dest === 'string' ? await doc.getDestination(dest) : dest;
		const ref = Array.isArray(resolved) ? resolved[0] : null;
		if (!ref || typeof ref !== 'object') return null;
		return (await doc.getPageIndex(ref as never)) + 1;
	} catch {
		return null;
	}
}
