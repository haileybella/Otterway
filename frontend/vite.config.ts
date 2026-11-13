import react from '@vitejs/plugin-react';
import basicSsl from '@vitejs/plugin-basic-ssl';
import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

// `npm run dev:phone` serves over HTTPS on your Wi-Fi so a phone can open it.
// Phones only allow location and microphone access over HTTPS.
export default defineConfig(({ mode }) => {
  const phone = mode === 'phone';
  return {
    plugins: [
      react(),
      ...(phone ? [basicSsl()] : []),
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.png', 'apple-touch-icon.png', 'otter.png', 'otter-face.png'],
        manifest: {
          name: 'Otterway',
          short_name: 'Otterway',
          description: 'Flood-aware navigation with Ollie, your voice guide.',
          theme_color: '#F5EEDD',
          background_color: '#F5EEDD',
          display: 'standalone',
          orientation: 'portrait',
          start_url: '/',
          icons: [
            { src: 'pwa-192.png', sizes: '192x192', type: 'image/png' },
            { src: 'pwa-512.png', sizes: '512x512', type: 'image/png' },
            { src: 'pwa-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
          ],
        },
        workbox: {
          // Keep recently viewed map tiles for offline use.
          runtimeCaching: [
            {
              urlPattern: /^https:\/\/tile\.openstreetmap\.org\/.*/i,
              handler: 'CacheFirst',
              options: {
                cacheName: 'map-tiles',
                expiration: { maxEntries: 500, maxAgeSeconds: 60 * 60 * 24 * 7 },
              },
            },
          ],
        },
      }),
    ],
    server: phone ? { host: true } : undefined,
  };
});
