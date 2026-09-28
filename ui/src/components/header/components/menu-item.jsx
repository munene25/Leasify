import { NavLink } from "react-router-dom";
import { twMerge } from "tailwind-merge";

const baseStyle =
  "group flex items-center h-fill w-fit text-primary border-b-4 border-transparent";
const active = "border-border";

// The menu item has height set to fill. Parent has to set height.
const MenuItem = ({ text, navigateTo }) => {
  return (
    <NavLink
      to={navigateTo}
      className={({ isActive }) => twMerge(baseStyle, isActive && active)}
    >
      <span className="group-hover:bg-foreground/20 rounded px-4 py-2 text-base capitalize">
        {text}
      </span>
    </NavLink>
  );
};

export default MenuItem;
