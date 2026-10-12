import { useState } from "react";
import { Eye, EyeClosed, Lock } from "lucide-react";

import InputField from "@components/form/input-field";

const PasswordField = ({ name = "password", label = "Password", autoComplete="" }) => {
	const [isPassword, setIsPassword] = useState(true);

	return (
		<div className="flex items-start justify-between gap-4">
			<InputField
				name={name}
				type={isPassword ? "password" : "text"}
				required={false}
                label={label}
                autoComplete={autoComplete}
				placeholder="e.g., Doe">
				<Lock size={15} />
			</InputField>

			<button
				className="p-2 mt-5 border rounded-md cursor-pointer bg-input text-primary-foreground"
				onClick={() => setIsPassword((val) => !val)}
				type="button">
				{isPassword ? <Eye size={18} /> : <EyeClosed size={18} />}
			</button>
		</div>
	);
};

export default PasswordField;
