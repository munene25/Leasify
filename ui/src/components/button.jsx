import { twMerge } from "tailwind-merge";
import { useFormContext } from "@context/form-context";

const buttonVariants = {
	baseStyle:
		"inline-flex transition-all duration-100 items-center justify-center gap-1.5 px-6 py-2 border border-transparent rounded-md shadow-md cursor-pointer font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none",

	primaryStyle:
		"bg-primary-foreground text-primary hover:bg-primary-foreground/95 active:bg-primary-foreground/60",

	primaryAltStyle:
		"bg-background text-primary-foreground hover:bg-background/95 active:bg-background/60",

	secondaryStyle: "bg-accent text-accent-foreground hover:bg-accent/95 active:bg-accent/60",

	secondaryAltStyle: "bg-foreground/50 text-background hover:bg-foreground/40 active:opacity-60",

	tertiaryStyle: "rounded-none shadow-none border-b-primary text-primary hover:opacity-95",

	tertiaryAltStyle:
		"bg-transparent rounded-none shadow-none border-b-transparent text-primary-foreground hover:border-b-primary-foreground",
};

const Button = ({
	variant = "primaryStyle",
	className = "",
	type = "button",
	onClick,
	children,
}) => {
	const formContext = useFormContext();
	const loading = formContext?.loading ?? false;

	return (
		<button
			type={type}
			disabled={loading}
			className={twMerge(buttonVariants.baseStyle, buttonVariants[variant], className)}
			onClick={onClick}>
			{children}
		</button>
	);
};

export default Button;
