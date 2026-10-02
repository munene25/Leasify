const InputError = ({ errors, field, loading }) => {
	if (!errors?.[field]?.length || loading) return null;
	return (
		<div className="py-2 space-y-2">
			{errors[field].map((msg) => (
				<p className="px-4 py-2 text-xs font-light text-red-800 bg-red-100 border border-red-300 rounded-sm">{msg}</p>
			))}
		</div>
	);
};

export default InputError;
