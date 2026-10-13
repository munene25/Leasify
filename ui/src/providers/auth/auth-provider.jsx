import React from "react";
import { FadeLoader } from "react-spinners";

import api from "@api/api";
import { AuthContext } from "@context/auth-context";
import { clearSessionStamp, markSessionStamp, useSessionKeepAlive } from "@providers/auth/session-refresh";


const AuthProvider = ({ children }) => {
	const [user, setUser] = React.useState(null);
	const [loading, setLoading] = React.useState(false);

	// Having a boolean prevents state rerenders on object change
	const isAuthenticated = Boolean(user);

	// Set user null on 401
	const logoutUser = () => {
		setUser(null);
		clearSessionStamp();
		console.log("User logged out");
	};

	// Fetch user and set state
	const fetchUser = async () => {
		setLoading(true);

		try {
			const response = await api.get("users/me");
			setUser(response.data);
		} catch (error) {
			console.log("Could not fetch user", error);
			logoutUser();
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		fetchUser();
	}, []);

	// Custom Session keep alive hook
	useSessionKeepAlive(isAuthenticated, markSessionStamp, logoutUser);

	return (
		<AuthContext.Provider value={{ user, setUser, fetchUser }}>
			{loading ? <LoadingPage /> : children}
		</AuthContext.Provider>
	);
};

export default AuthProvider;

const LoadingPage = () => {
	return (
		<div className="flex items-center justify-center w-screen h-screen bg-secondary">
			<FadeLoader size={25} color="var(--color-primary)" />
		</div>
	);
};
