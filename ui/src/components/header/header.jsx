import { useNavigate } from "react-router-dom";

import logoLight from "@assets/logo/logo-light.svg";
import MenuItem from "@components/header/components/menu-item";
import Button from "@components/button";

export default function Header() {
  const navigate = useNavigate()
  return (
    <header className="flex items-center justify-center h-20 bg-primary-foreground position-fix">
      <div className="flex items-center max-w-6xl y-between h-fill">
        {/* Left-most Logo icon and text */}
        <figure className="w-fit">
          <img src={logoLight} alt="Leasify Logo" />
        </figure>

        {/* Navlinks Center*/}
        <nav className="flex gap-8 w-fit h-fill">
          <MenuItem text="Home" navigateTo="/" />
          <MenuItem text="Apartments" navigateTo="/apartments" />
          <MenuItem text="How-it-works" navigateTo="/flow" />
          <MenuItem text="Ammenities" navigateTo="/amenities" />
          <MenuItem text="Support" navigateTo="/support" />
        </nav>

        {/* Sign up sign in */}
        <div className="flex items-center gap-2">
          <Button variant="secondaryAlt" onClick={() => navigate("/login")} >Log in</Button>
          <Button variant="primaryAlt" onClick={() => navigate("/signup")} >Sign up</Button>
        </div>
      </div>
    </header>
  );
}
