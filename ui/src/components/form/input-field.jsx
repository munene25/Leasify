import { cn } from "cn";

import { useFormContext } from "@context/form-context";
import InputError from "@components/form/input-error";

const InputField = ({
	name,
	type,
	required,
	children,
	label = "",
	autoComplete = "",
	placeholder = "",
}) => {
	const { form, handleChange, loading, errors, } = useFormContext();

	const fieldErrors = errors?.[name] ?? [];
	const hasError = fieldErrors.length > 0;

	return (
		<div className={cn("w-full space-y-1")}>
			{/* Label if any*/}
			<label htmlFor={name} className="block text-sm font-medium text-foreground">
				{label}
				{required && (<span className="ml-1 text-destructive" aria-hidden="true">*</span>)}
			</label>

			{/* Icon and Field */}
			<div
				className={cn(
					"flex items-center gap-1 rounded shadow-xs border bg-input px-2 py-1 focus-within:ring-2 focus-within:ring-ring/30 focus-within:border-transparent",
					{ "border-destructive focus-within:ring-destructive/30": hasError },
					{ "opacity-70": loading },
				)}>
				
				{children && <span className="shrink-0 text-muted-foreground">{children}</span>}

				{/* Input */}
				<input
					id={name}
					name={name}
					type={type}
					value={form[name] ?? ""}
					onChange={handleChange}
					required={required}
					placeholder={placeholder}
					autoComplete={autoComplete}
					disabled={loading}
					aria-invalid={hasError}
					aria-describedby={hasError ? `${name}-error` : undefined}
                    className="flex-1 min-w-0 px-2 py-1 text-sm border-none rounded outline-none bg-none focus-within:bg-none text-foreground placeholder:text-muted-foreground"
				/>
			</div>
			<InputError errors={fieldErrors} loading={loading} />
		</div>
	);
};

export default InputField;
