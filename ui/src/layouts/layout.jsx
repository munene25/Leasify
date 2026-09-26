import Main from "@layouts/main-content";
import Header from "@components/header/header";

export default function Layout({ children }) {
  return (
    <div>
      <Header />
      <Main>{children}</Main>
    </div>
  );
}
