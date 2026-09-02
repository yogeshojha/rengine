import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig, type Plugin } from 'vite';

// vite-plugin-svelte 6.x can serve the raw .svelte source for a component's `?type=style&lang.css`
// virtual module (compiled-CSS cache miss); recover the <style> body before @tailwindcss/vite parses
// its <script> as CSS ("Invalid declaration"). Fixed upstream in vite-plugin-svelte 7.1.x (needs Vite 8).
function svelteStyleCssLeakGuard(): Plugin {
	return {
		name: 'svelte-style-css-leak-guard',
		enforce: 'pre',
		transform(code, id) {
			if (!/\.svelte\?.*\btype=style\b/.test(id)) return;
			if (!/<\/?(?:script|style|template)\b/i.test(code)) return;
			const style = code.match(/<style[^>]*>([\s\S]*?)<\/style>/i);
			return { code: style ? style[1] : '', map: null };
		}
	};
}

export default defineConfig({
	plugins: [sveltekit(), svelteStyleCssLeakGuard(), tailwindcss()],
	optimizeDeps: {
		exclude: ['bits-ui']
	},
	ssr: {
		noExternal: ['bits-ui', 'tailwind-variants']
	},
	server: {
		proxy: {
			'/api': {
				target: 'http://api:8000',
				changeOrigin: true,
				configure: (proxy) => {
					proxy.on('proxyRes', (proxyRes, _req, res) => {
						if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
							setImmediate(() => res.flushHeaders());
						}
					});
				}
			}
		}
	}
});
