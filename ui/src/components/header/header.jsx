import { useNavigate } from "react-router-dom";

import logoLight from "@assets/logo/logo-light.svg";
import MenuItem from "@components/header/menu-item";
import Button from "@components/button";
import { MdLogin } from "react-icons/md";

export default function Header() {
  const navigate = useNavigate();
  return (
    <header className="flex items-center justify-center h-16 bg-primary-foreground position-fix">
      <div className="flex items-center justify-between w-full h-full max-w-7xl">
        {/* Left-most Logo icon and text */}
        <figure className="w-fit">
          <img src={logoLight} alt="Leasify Logo" className="scale-110" />
        </figure>

        {/* Navlinks Center*/}
        <nav className="inline-flex h-full gap-2 w-fit">
          <MenuItem text="Home" navigateTo="/" />
          <MenuItem text="Apartments" navigateTo="/apartments" />
          <MenuItem text="How-it-works" navigateTo="/flow" />
          <MenuItem text="Ammenities" navigateTo="/amenities" />
          <MenuItem text="Support" navigateTo="/support" />
        </nav>

        {/* Sign up sign in */}
        <div className="flex items-center gap-4">
          
          {/* Login */}
          <Button
            variant="tertiaryStyle"
            className="text-sm"
            onClick={() => navigate("/login")}
          >
            Login
            <MdLogin />
          </Button>
          
          {/* Signup */}
          <Button
            variant="secondaryAltStyle"
            className="text-sm"
            onClick={() => navigate("/signup")}
          >
            Sign up
          </Button>
        </div>
      </div>
    </header>
  );
}
