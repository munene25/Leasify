import "@assets/styles/globals.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "@layouts/layout";
import HomePage from "@pages/home";

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
