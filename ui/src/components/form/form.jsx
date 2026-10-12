import { cn } from "cn";
import { MoonLoader } from "react-spinners";
import { FormContext } from "@/context/form-context";

const Form = ({
	form,
	loading,
	errors,
	handleSubmit,
	handleChange,
	children,
	title = "",
	className = "",
}) => {
	return (
		<FormContext.Provider value={{ form, handleChange, loading, errors }}>
			<form
				className={cn(
					"px-8 py-4 border rounded-md shadow bg-primary",
					className,
				)}
				onSubmit={handleSubmit}>
				{/* Title and loader */}
				<div className="flex items-center justify-between py-2">
					<h2 className="capitalize text-primary-foreground">{title}</h2>
					<MoonLoader
						loading={loading}
						color="var(--color-primary-foreground)"
						speedMultiplier={0.65}
						size={22}
					/>
				</div>
				{children}
			</form>
		</FormContext.Provider>
	);
};

export default Form;
