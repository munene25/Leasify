import "@assets/styles/globals.css";

import { BrowserRouter, Routes, Route } from "react-router-dom";

import Layout from "@layouts/layout";
import HomePage from "@pages/home";
import LoginPage from "@pages/login";
import AmenitiesPage from "@pages/amenities";

function App() {
	return (
		<BrowserRouter>
			<Layout>
				<Routes>
					<Route path="/" element={<HomePage />} />
					<Route path="/login" element={<LoginPage />} />
					<Route path="/signup" element={<AmenitiesPage />} />
					<Route path="/amenities" element={<HomePage />} />
				</Routes>
			</Layout>
		</BrowserRouter>
	);
}

export default App;
