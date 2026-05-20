import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "src"),
        },
    },
    server: {
        host: true,
        port: 5173,
        // Polling is required because the source lives on a Windows host
        // bind-mounted into a Linux container — inotify events don't propagate.
        watch: {
            usePolling: true,
            interval: 500,
        },
        proxy: {
            "/api": {
                target: "http://app:8000",
                changeOrigin: true,
            },
        },
    },
    test: {
        environment: "jsdom",
        globals: true,
        setupFiles: ["./src/test-setup.ts"],
    },
});
