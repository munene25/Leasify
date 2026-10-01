import { createContext, useContext } from "react";

const FormContext = createContext(null);

const useFormContext = () => {
    const context = useContext(FormContext);
    
	if (context === undefined) {
		throw new Error("useFormContext must be used within FormContext.Provider");
	}
	return context;
};

export {FormContext, useFormContext}