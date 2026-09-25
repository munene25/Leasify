import path from "path";

import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import {visualizer} from 'rollup-plugin-visualizer';

// https://vite.dev/config/
export default defineConfig({
	plugins: [react(), tailwindcss(),visualizer({open:true})],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "./src"),
			"@components": path.resolve(__dirname, "./src/components"),
			"@hooks": path.resolve(__dirname, "./src/hooks"),
			"@utils": path.resolve(__dirname, "./src/utils"),
			"@assets": path.resolve(__dirname, "./src/assets"),
			"@layouts": path.resolve(__dirname, "./src/layouts"),
			"@pages": path.resolve(__dirname, "./src/pages"),
			"@styles": path.resolve(__dirname, "./src/styles"),
			"@api": path.resolve(__dirname, "./src/api"),
		},
	},
});