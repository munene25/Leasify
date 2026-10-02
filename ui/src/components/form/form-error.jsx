import { CircleAlert } from "lucide-react";

export function FormError({ errors, loading }) {
	if (!errors?.general?.length || loading) return null;

	return (
		<div className="py-2 space-y-2">
			{errors.general.map((error) => (
				<span
					key={error}
					className="flex items-center gap-2 px-4 py-2 text-sm rounded bg-destructive/50 text-secondary-foreground">
					<CircleAlert size={15} className="shrink-0" />
					{error}
				</span>
			))}
		</div>
	);
}
