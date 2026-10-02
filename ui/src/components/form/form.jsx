import { twMerge } from "tailwind-merge";
import { MoonLoader } from "react-spinners";

const Form = ({ loading, onSubmit, children, title = "", description = "", className = "" }) => {
	return (
		<div className={twMerge("px-8 py-4 border rounded-md shadow bg-primary", className)}>
			{/* Title and loader */}
			<div className="py-4">
				<div className="flex items-center justify-between py-2">
					<h3 className="text-primary-foreground">{title}</h3>
					
					<MoonLoader
						loading={loading}
						color="var(--color-primary-foreground)"
						speedMultiplier={0.65}
						size={22}
					/>
				</div>
				<p className="text-sm text-secondary-foreground">{description}</p>
			</div>

			{/* Form Section */}
			<form className="py-2 space-y-2" onSubmit={onSubmit}>
				{children}
			</form>
		</div>
	);
};

export default Form;
