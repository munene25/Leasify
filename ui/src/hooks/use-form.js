import { useState } from "react";
import { parseErrors } from "@api/parse-errors";

export default function useForm(handleSubmit) {
	const [loading, setLoading] = useState(false);
	const [errors, setErrors] = useState({});
	const [form, setForm] = useState({});

	const handleChange = (e) => {
		// setErrors({});
		setForm((prev) => ({
		  ...prev,
		  [e.target.name]: e.target.value,
		}));
	  };

	const onSubmit = async (event) => {
		event.preventDefault();
		setLoading(true);
		setErrors({});

		try {
			await handleSubmit(form);
		} catch (err) {
			console.log(err);
			setErrors(parseErrors(err));
		} finally {
			setLoading(false);
		}
	};

	return { form, setForm, errors, setErrors, loading, handleChange, onSubmit };
}
