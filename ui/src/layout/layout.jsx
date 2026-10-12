import  SmoothScroll  from "@layout/smooth-scroll";
import Main from "@layout/main-content";
import Header from "@components/header/header";

const Layout = ({ children }) =>  {
	return (
		<SmoothScroll>
			<Header />
			<Main>{children}</Main>
		</SmoothScroll>
	);
}

export default Layout