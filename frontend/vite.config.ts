import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { compile } from 'svelte/compiler';
import { defineConfig, type Plugin } from 'vite';

// vite-plugin-svelte 6.x serves raw .svelte source for `?type=style`. Fixed in 7.1.x, which needs Vite 8.
function svelteStyleCssLeakGuard(): Plugin {
	return {
		name: 'svelte-style-css-leak-guard',
		enforce: 'pre',
		transform(code, id) {
			if (!/\.svelte\?.*\btype=style\b/.test(id)) return;
			if (!/<\/?(?:script|style|template)\b/i.test(code)) return;
			const filename = id.split('?')[0];
			try {
				return { code: compile(code, { filename, generate: 'client' }).css?.code ?? '', map: null };
			} catch {
				return { code: '', map: null };
			}
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
