import InputField from "@components/form/input-field";
import { Eye, EyeClosed, Lock } from "lucide-react";
import { useState } from "react";

const PasswordField = ({ form, onChange, errors }) => {
	const [isPassword, setIsPassword] = useState(true);

	return (
		<div className="flex items-end justify-between gap-4">
			<InputField
				name="password"
				type={isPassword ? "password" : "text"}
				required={false}
				value={form.password}
				onChange={onChange}
				errors={errors}
				label="Password"
				placeholder="e.g., Doe">
				<Lock size={15} />
			</InputField>

			<button
				className="p-2 border rounded-md cursor-pointer bg-input text-primary-foreground hover:bg-input-50"
				onClick={() => setIsPassword((val) => !val)}
				type="button">
				{isPassword ? <Eye size={18} /> : <EyeClosed size={18} />}
			</button>
		</div>
	);
};

export default PasswordField;
