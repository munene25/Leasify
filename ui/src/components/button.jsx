import { twMerge } from "tailwind-merge";

const buttonVariants = {
  baseStyle:
    "inline-flex items-center justify-center gap-1.5 px-6 py-2 border border-transparent rounded-md shadow-md cursor-pointer font-mediumcons focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:grayscale",

  primaryStyle:
    "bg-primary-foreground text-primary hover:bg-primary/90 active:bg-primary/60",

  primaryAltStyle:
    "bg-background text-primary-foreground hover:bg-primary/80 active:bg-primary/60",

  secondaryStyle:
    "bg-accent text-accent-foreground hover:bg-accent/80 active:bg-accent/60",

  secondaryAltStyle:
    "text-background bg-foreground/30 hover:bg-foreground/40 active:opacity-60",

  tertiaryStyle:
    "p-0 text-primary-foreground underline-offset-4 hover:underline",

  tertiaryAltStyle:
    "p-0 underline text-primary-foreground underline-offset-4 hover:opacity-80",
};

export default function Button({
  variant = "primaryStyle",
  onClick,
  className = "",
  children,
}) {
  return (
    <button
      className={twMerge(
        buttonVariants.baseStyle,
        buttonVariants[variant],
        className,
      )}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
