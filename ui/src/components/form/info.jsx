import { cn } from "cn";
import { InfoIcon, CircleX } from "lucide-react";
import React from "react";

const Info = ({ className = "", text = "", cancelable = false }) => {
	const [vissible, setVissible] = React.useState(true);

	if (!vissible) return null;
	return (
		<div
			className={cn(
				"flex justify-between items-center w-full px-8 py-4 rounded-md bg-popover text-popover-foreground text-sm font-medium",
				className,
			)}>
			<span className="inline-flex items-center gap-1">
				<InfoIcon size={12} />
				{text}
			</span>
			{cancelable && (
				<CircleX
					className="transition-all cursor-pointer hover:rotate-45"
					onClick={() => setVissible((prev) => !prev)}
					size={15}
				/>
			)}
		</div>
	);
};

export default Info;
