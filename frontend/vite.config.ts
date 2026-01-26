import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
    plugins: [sveltekit(), tailwindcss()],
    optimizeDeps: {
        exclude: ['bits-ui']
    },
    ssr: {
        noExternal: ['bits-ui', 'tailwind-variants']
    },
    server: {
        proxy: {
            '/api': {
                target: 'http://backend:8000',
                changeOrigin: true
            }
        }
    }
});
