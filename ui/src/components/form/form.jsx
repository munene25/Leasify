import { twMerge } from "tailwind-merge";
import { FadeLoader } from "react-spinners";

import useForm from "@hooks/use-form-submit";
import FormContext from "@context/form-context";

const formClass = {
	baseStyle: "px-4 py-2 border rounded bg-primary",
};

const Form = ({
	title = "",
	description = "",
	className = "",
	handleSubmit,
	children,
}) => {
	const { onSubmit, loading, errors } = useForm(handleSubmit);

	return (
		<FormContext.Provider
			value={{
				onSubmit,
				loading,
				errors,
			}}
		>
			<div className={twMerge(formClass.baseStyle, className)}>
				{/* Title and loader */}
				<div className="flex items-center justify-between">
					<h4 className="text-primary-foreground">{title}</h4>
					<FadeLoader
						size={5}
						color="var(--color-primary)"
						speedMultiplier={0.65}
					/>
				</div>
				<p className="text-sm text-secondary-foreground">{description}</p>

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
