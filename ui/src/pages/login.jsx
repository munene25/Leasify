import { useState } from "react";
import { User } from "lucide-react";

import Form from "@components/form/form";
import InputField from "@components/form/input-field";
import Button from "@components/button";

const LoginPage = () => {
	const [form, setForm] = useState({});

	const handleChange = (e) => {
		setForm((prev) => ({
			...prev,
			[e.target.name]: e.target.value,
		}));
	};

	const handleSubmit = async () => {
		console.log(form);
		setForm({});
		const waitOut = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
		await waitOut(2000);
	};

	return (
		<div className="flex items-start justify-center w-screen h-screen pt-40">
			<Form
				className="min-w-xl"
				title="Login"
				description="Login to access your account"
				handleSubmit={handleSubmit}>
				<InputField
					name="first_name"
					type="text"
					required={false}
					value={form.first_name}
					onChange={handleChange}
					label="First name"
					placeholder="e.g., John">
					<User size={18} />
				</InputField>

				<InputField
					name="last_name"
					type="text"
					required={false}
					value={form.last_name}
					onChange={handleChange}
					label="Last name"
					placeholder="e.g., Doe">
					<User size={18} />
				</InputField>
				<div className="py-4">
				<Button type="submit" className="w-full">
					Login
				</Button>

				</div>
			</Form>
		</div>
	);
};

export default LoginPage;
