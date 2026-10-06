import Main from "@layouts/main-content";
import Header from "@components/header/header";
import { SmoothScroll } from "@layout/smooth-scroll";

export default function Layout({ children }) {
	return (
		<SmoothScroll>
			<Header />
			<Main>{children}</Main>
		</SmoothScroll>
	);
}
