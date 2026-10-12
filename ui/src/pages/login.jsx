import { Mail } from "lucide-react";
import { useNavigate } from "react-router-dom";

import api from "@api/api";
import Form from "@components/form/form";
import InputField from "@components/form/input-field";
import Button from "@components/button";
import useForm from "@hooks/use-form";
import PasswordField from "@components/form/password-field";
import Info from "@components/form/info";

const LoginPage = () => {
	const navigate = useNavigate();

	const submitForm = async (form) => {
		response = await api.post("auth/login", form);
		console.log(response);
	};

	const validateForm = (form) => {
		const errors = {};
		const email = form.email ?? "";
		if (!(email.includes(".") || !email.includes("@"))) {
			errors.email = ["Please enter a valid email address"];
		}
		return errors;
	};

	const { form, handleChange, handleSubmit, loading, errors } = useForm(
		submitForm,
		validateForm,
	);

	return (
		<div className="flex items-start justify-center w-screen h-screen pt-40">
			<Form
				form={form}
				handleChange={handleChange}
				handleSubmit={handleSubmit}
				loading={loading}
				errors={errors}
				title="login"
				className="min-w-lg">
				<p className="pb-4 text-sm text-secondary-foreground">
					Login to continue.
				</p>
				<Info text="Please input the email and username." className="mb-2" />
				<div className="space-y-2">
					<InputField
						name="email"
						type="text"
						label="E-mail"
						autoComplete="email"
						required
						placeholder="email@example.com">
						<Mail size={16} />
					</InputField>
					<PasswordField autoComplete="current-password"  />
				</div>

				<Button type="submit" className="w-full my-4" loading={loading}>
					Login
				</Button>
			</Form>
		</div>
	);
};

export default LoginPage;
