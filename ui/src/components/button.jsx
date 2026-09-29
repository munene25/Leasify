import { twMerge } from "tailwind-merge";

const buttonVariants = {
  baseStyle:
    "inline-flex items-center justify-center gap-2 px-6 py-2 font-medium transition-all duration-100 border border-transparent rounded shadow-md cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:grayscale",

  primaryStyle:
    "bg-primary-foreground text-primary hover:bg-primary/90 active:bg-primary/60",

  primaryAltStyle:
    "bg-background text-primary-foreground hover:bg-primary/80 active:bg-primary/60",

  secondaryStyle:
    "bg-accent text-accent-foreground hover:bg-accent/80 active:bg-accent/60",

  secondaryAltStyle:
    "text-background border-background/80 hover:opacity-80 active:opacity-60",

  tertiaryStyle:
    "p-0 text-primary-foreground underline-offset-4 hover:underline",

  tertiaryAltStyle:
    "p-0 underline text-primary-foreground underline-offset-4 hover:opacity-80",
};

export default function Button({
  variant = "primary",
  onClick,
  className = "",
  children,
}) {
  return (
    <button
      className={twMerge(
        buttonVariants.base,
        buttonVariants[variant],
        className,
      )}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
