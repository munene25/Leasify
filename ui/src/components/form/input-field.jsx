const InputField = ({
	name,
	type,
	required,
	onChange,
	children,
	label = "",
	value = "",
	autoComplete = true,
	placeholder = "",
}) => {
	return (
		<div className="transition-all duration-100 spacy-y-4">
			{/* Label if any*/}
			{label && (
				<label htmlFor={name} className="font-medium text-secondary-foreground">
					{label}
					{required && <span className="pl-2 text-accent">*</span>}
				</label>
			)}
			{/* Icon and Field */}
			<span className="flex items-center gap-2 px-4 py-2 border rounded-md bg-input focus-within:ring-1 focus-within:ring-offset-1">
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
					autoComplete={autoComplete}
					className="flex-1 outline-none bg-none placeholder:text-input-foreground/80 focus:outline-none"
				/>
			</span>
		</div>
	);
};

export default InputField;
