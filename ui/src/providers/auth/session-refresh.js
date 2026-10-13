/* 
Provide a means to set and manage cookie age to avoid session expiry
Setting and clearing localstorage timestamps is required in login as well as logout

We need to watch out for expired sessions. In the case that the user state is populated but the session is expired. Maybe an interceptor?
*/
import api from "@api/api";
import { useEffect } from "react";
import { refreshSession } from "@session-refresh";

const KEY = "session:lastRefresh";
const INTERVAL = 7 * 24 * 60 * 60 * 1000; // 3 days in ms

const markSessionStamp = () => localStorage.setItem(KEY, String(Date.now()));
const clearSessionStamp = () => localStorage.removeItem(KEY);

// Refresh session on pagevisibility
const useSessionKeepAlive = (isAuthenticated, successRefresh, failRefresh) => {
	useEffect(() => {
		if (!isAuthenticated) return;

		// Handle refresh logic
		const refreshSession = async (successRefresh, failRefresh) => {
			const lastRefresh = Number(localStorage.getItem(KEY)) || 0;
			const elapsed = Date.now() - lastRefresh;

			// Session considered fresh
			if (elapsed >= 0 && elapsed < INTERVAL) return;

			try {
				await api.post("auth/refresh");
				successRefresh();

				// Catches 401 and handlesFail
			} catch (error) {
				console.log("Could not refresh session", error);
				if (error?.response?.status === 401) {
					failRefresh();
				}
			}
		};

		const handleVisible = () => {
			if (document.visibilityState !== "visible") return;
			refreshSession(successRefresh, failRefresh);
		};

		// initial mount
		handleVisible();

		// Add event listener
		document.addEventListener("visibilitychange", handleVisible);

		// Cleanup
		return () => {
			document.removeEventListener("visibilitychange", handleVisible);
		};
	}, [isAuthenticated]);
};

export { markSessionStamp, clearSessionStamp, useSessionKeepAlive };
