import { ReactLenis } from "lenis/react";
import "lenis/dist/lenis.css";

const SmoothScroll = ({ children }) => {
	return <ReactLenis root>{children}</ReactLenis>;
};

export default SmoothScroll;
