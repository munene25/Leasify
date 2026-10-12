import { useState } from "react";
import { parseErrors } from "@api/parse-errors";

export default function useForm(submitForm, validateForm = () => null) {

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

	const handleSubmit = async (event) => {
        event.preventDefault();
        setErrors({});
        
        const validationErrors = validateForm(form);
        if (validationErrors) {
            setErrors(validationErrors);
            return;
        }

        setLoading(true);
        
		try {
			await submitForm(form);
		} catch (err) {
			console.log(err);
			setErrors(parseErrors(err));
		} finally {
			setLoading(false);
		}
	};

	return { form, setForm, errors, setErrors, loading, handleChange, handleSubmit };
}
