import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(() => {
    const basePath = process.env.LLAMA_DEPLOY_DEPLOYMENT_BASE_PATH;
    const port = process.env.PORT ? parseInt(process.env.PORT) : undefined;

    return {
        plugins: [react()],
        server: { port, host: true, hmr: { port } },
        base: basePath,
        build: {
            outDir: "dist",
        },
        define: {
            ...(basePath && {
                "import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_BASE_PATH":
                    JSON.stringify(basePath),
            }),
            ...(process.env.LLAMA_DEPLOY_DEPLOYMENT_NAME && {
                "import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME": JSON.stringify(
                    process.env.LLAMA_DEPLOY_DEPLOYMENT_NAME,
                ),
            }),
            ...(process.env.LLAMA_DEPLOY_PROJECT_ID && {
                "import.meta.env.VITE_LLAMA_DEPLOY_PROJECT_ID": JSON.stringify(
                    process.env.LLAMA_DEPLOY_PROJECT_ID,
                ),
            }),
        },
    };
});
