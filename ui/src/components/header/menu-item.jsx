import { NavLink } from "react-router-dom";
import { twMerge } from "tailwind-merge";

const variants = {
  baseStyle:
    "flex items-center h-full border-b-4 border-transparent w-fit text-primary hover:border-border",
  activeStyle: "border-border text-accent",
};

// The menu item has height set to fill. Parent has to set height.
const MenuItem = ({ text, navigateTo }) => {
  return (
    <NavLink
      to={navigateTo}
      className={({ isActive }) =>
        twMerge(variants.baseStyle, isActive && variants.activeStyle)
      }
    >
      <span className="px-4 py-2 text-base capitalize rounded">{text}</span>
    </NavLink>
  );
};

export default MenuItem;
