import InputError from "@components/form/input-error";

const InputField = ({
	name,
	type,
	required,
	onChange,
	errors,
	children,
	label = "",
	value = "",
	placeholder = "",
}) => {
	return (
		<div className="w-full text-sm transition-all duration-100">
			{/* Label if any*/}
			<label htmlFor={name} className="font-medium text-secondary-foreground">
				{label}
				{required && <span className="pl-2 font-bold text-accent">*</span>}
			</label>

			{/* Icon and Field */}
			<span className="flex items-center gap-2 px-4 py-2 border rounded-md bg-input focus-within:ring-1">
				{children}
				{/* Input */}
				<input
					id={name}
					name={name}
					type={type}
					value={value}
					onChange={onChange}
					required={required}
					placeholder={placeholder}
					autoComplete={name}
					className="flex-1 outline-none bg-none placeholder:text-input-foreground/80 focus:outline-none"
				/>
			</span>
			<InputError errors={errors} field={name} />
		</div>
	);
};

export default InputField;
