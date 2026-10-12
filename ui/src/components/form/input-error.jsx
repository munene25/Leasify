import { CircleAlert } from "lucide-react";

const InputError = ({ errors, loading }) => {
	if (!errors.length || loading) return null;
	return (
		<div className="space-y-1.5">
			{errors.map((msg, index) => (
				<p
					key={index}
					className="flex items-center gap-1.5 text-xs text-destructive">
					<CircleAlert
						size={12}
						className="shrink-0"
						aria-hidden="true"
					/>
					<span>{msg}</span>
				</p>
			))}
		</div>
	);
};

export default InputError;
