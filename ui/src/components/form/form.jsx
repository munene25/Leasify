import { twMerge } from "tailwind-merge";
import { MoonLoader } from "react-spinners";

import useForm from "@hooks/use-form";
import { FormContext } from "@context/form-context";

const Form = ({ title = "", description = "", className = "", handleSubmit, children }) => {
	// Custom form hook
	// Consider adding form setForm state?
	const { onSubmit, loading, errors } = useForm(handleSubmit);

	return (
		<FormContext.Provider
			value={{
				onSubmit,
				loading,
				errors,
			}}>
			<div className={twMerge("px-8 py-4 border rounded-md shadow bg-primary", className)}>
				{/* Title and loader */}
				<div className="py-2">
					<div className="flex items-center justify-between py-2">
						<h3 className="text-primary-foreground">{title}</h3>
						<MoonLoader loading={loading} color="var(--color-primary-foreground)" speedMultiplier={0.65} size={20} />
					</div>
					<p className="text-sm text-secondary-foreground">{description}</p>
				</div>

				{/* Form Section */}
				<form className="py-2 space-y-2" onSubmit={onSubmit}>
					{/* Form Children */}
					{children}
				</form>
			</div>
		</FormContext.Provider>
	);
};

export default Form;
