import { useState } from "react";
import { parseErrors } from '@api/parse-errors';

export function useForm(handleSubmit) {
	const [loading, setLoading] = useState(false);
	const [errors, setErrors] = useState("");

	const onSubmit = async (event) => {
		event.preventDefault();
		setLoading(true);
		setErrors("");

		try {
			await handleSubmit();
		} catch (err) {
			console.log(err);
			setErrors(parseErrors(err));
		} finally {
			setLoading(false);
		}
	};

	return { onSubmit, loading, errors };
}
