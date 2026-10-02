import { User } from "lucide-react";

import Form from "@components/form/form";
import InputField from "@components/form/input-field";
import Button from "@components/button";
import useForm from "@hooks/use-form";
import waitFor from "@/test-form-response";
import PasswordField from "@components/form/password-field";

const LoginPage = () => {
	const handleSubmit = async (form) => {
		await waitFor(8000, false);
		console.log(form);
	};

	const { form, handleChange, onSubmit, loading, errors } = useForm(handleSubmit);

	return (
		<div className="flex items-start justify-center w-screen h-screen pt-40">
			<Form
				className="min-w-xl"
				title="Login"
				description="Login to access your account"
				loading={loading}
				onSubmit={onSubmit}>
				<div className="flex items-start gap-4">
					<InputField
						name="first_name"
						type="text"
						required={false}
						value={form.first_name}
						errors={errors}
						onChange={handleChange}
						label="Full name"
						placeholder="First Name">
						<User size={15} />
					</InputField>

					<InputField
						name="last_name"
						type="text"
						required={false}
						errors={errors}
						value={form.last_name}
						onChange={handleChange}
						placeholder="Last Name">
						<User size={15} />
					</InputField>
				</div>
				<PasswordField onChange={handleChange} form={form} errors={errors} />

				<div className="py-4">
					<Button type="submit" className="w-full" loading={loading}>
						Login
					</Button>
				</div>
			</Form>
		</div>
	);
};

export default LoginPage;
