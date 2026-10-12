import { CircleAlert } from "lucide-react";

const InputError = ({ errors, loading }) => {
	if (!errors.length || loading) return null;
	return (
		<div className="space-y-1.5 pt-1">
			{errors.map((msg, index) => (
				<p
					key={index}
					className="inline-flex gap-1.5 text-xs font-medium text-destructive">
					<CircleAlert
						size={14}
						className="mt-0.5 shrink-0"
						aria-hidden="true"
					/>
					<span>{msg}</span>
				</p>
			))}
		</div>
	);
};

export default InputError;
