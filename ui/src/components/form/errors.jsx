import { BsExclamationCircle } from "react-icons/bs";
import { useFormContext } from "@context/form-context";

export function Errors() {
	const { errors, loading } = useFormContext();

	if (!errors?.length || loading) return null;

	return (
		<div className="flex flex-col gap-2">
			{errors.nonFormErrors.map((error) => (
				<div
					key={error}
					className="flex items-center gap-2 px-4 py-2 text-sm rounded bg-destructive/50 text-secondary-foreground"
				>
					<BsExclamationCircle size={15} className="shrink-0" />
					<span>{error}</span>
				</div>
			))}
		</div>
	);
}
