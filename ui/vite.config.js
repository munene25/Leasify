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
			"@components": path.resolve(import.meta.dirname, "./src/components"),
			"@hooks": path.resolve(import.meta.dirname, "./src/hooks"),
			"@context": path.resolve(import.meta.dirname, "./src/context"),
			"@utils": path.resolve(import.meta.dirname, "./src/utils"),
			"@assets": path.resolve(import.meta.dirname, "./src/assets"),
			"@layouts": path.resolve(import.meta.dirname, "./src/layouts"),
			"@pages": path.resolve(import.meta.dirname, "./src/pages"),
			"@styles": path.resolve(import.meta.dirname, "./src/styles"),
			"@api": path.resolve(import.meta.dirname, "./src/api"),
		},
	},
});