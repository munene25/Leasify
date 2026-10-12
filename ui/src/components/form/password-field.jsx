import { useState } from "react";
import { Eye, EyeClosed, Lock } from "lucide-react";

import InputField from "@components/form/input-field";

const PasswordField = ({
	name = "password",
    label = "Password",
    placeholder = "Paswword",
    autoComplete = "",
    required = false,
}) => {
	const [isPassword, setIsPassword] = useState(true);

	return (
		<div className="relative flex items-center justify-between gap-4">
			<InputField
				name={name}
				type={isPassword ? "password" : "text"}
				required={required}
				label={label}
				autoComplete={autoComplete}
				placeholder={placeholder}>
				<Lock size={15} />
				<button
					className="absolute top-[26px] right-0 p-2 cursor-pointer bg-none text-primary-foreground"
					onClick={() => setIsPassword((val) => !val)}
					type="button">
					{isPassword ? <EyeClosed size={18} /> : <Eye size={18} />}
				</button>
			</InputField>
		</div>
	);
};

export default PasswordField;
