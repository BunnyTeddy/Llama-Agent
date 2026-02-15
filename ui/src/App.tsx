import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";

const basePath =
    import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_BASE_PATH || "";
const deploymentName =
    import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME || "three-way-matcher";

export default function App() {
    return (
        <Routes>
            <Route path="/" element={<Home deploymentName={deploymentName} basePath={basePath} />} />
        </Routes>
    );
}
