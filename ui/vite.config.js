import path from "path";

import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
	plugins: [react(), tailwindcss()],
	resolve: {
		alias: {
			"@": path.resolve(import.meta.dirname, "./src"),
			"@api": path.resolve(import.meta.dirname, "./src/api"),
			"@assets": path.resolve(import.meta.dirname, "./src/assets"),
			"@components": path.resolve(import.meta.dirname, "./src/components"),
			"@context": path.resolve(import.meta.dirname, "./src/context"),
			"@hooks": path.resolve(import.meta.dirname, "./src/hooks"),
			"@layout": path.resolve(import.meta.dirname, "./src/layout"),
			"@pages": path.resolve(import.meta.dirname, "./src/pages"),
			"@providers": path.resolve(import.meta.dirname, "./src/providers"),
			"@styles": path.resolve(import.meta.dirname, "./src/styles"),
			"@utils": path.resolve(import.meta.dirname, "./src/utils"),
		},
	},
});