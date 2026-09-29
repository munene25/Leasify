import { useState } from "react";
import Button from "@/components/button";
import Loader from "@components/loader";
import { toast } from "sonner";
import { getErrorMessage } from "@/utils/handle-api-error";

const formSizes = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  xxl: "max-w-4xl",
};

const buttonAlignClasses = {
  left: "items-start",
  center: "items-center w-full",
  right: "items-end",
};

const Form = ({
  title = "",
  align = "right",
  divSize = "xxl",
  description = "",
  handleSubmit,
  visible = true,
  children,
  btnText = "Submit",
}) => {
  const [loading, setLoading] = useState(false);

  return (
    <div>
      {/* Loading state */}
      {loading && (
        <div className="flex flex-col items-center w-full gap-2 py-6 text-sm text-secondary-foreground">
          <span>Please wait, this won't take long...</span>
          <span className="text-accent">
            <MoonLoader size={20} color="var(--color-primary)" />
          </span>
        </div>
      )}

      {/* Success Message */}
      {message && !loading && (
        <div className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-md text-success-content bg-success">
          <MdCheckCircle size={15} className="w-4" />
          <span>{message}</span>
        </div>
      )}

      {/* Form Errors */}
      {formErrors && !loading && formErrors.length > 0 ? (
        <div className="flex flex-col gap-2">
          {formErrors.map((error, index) => (
            <div
              key={index}
              className="flex items-center gap-2 px-4 py-2 text-base rounded-lg text-error-content bg-error/90"
            >
              <BsExclamationCircle size={15} className="w-4" />
              <span>{error}</span>
            </div>
          ))}
        </div>
      ) : (
        formErrors && (
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg text-md text-error-content bg-error/90">
            <BsExclamationCircle size={15} className="w-4" />
            <span>Sorry, there was an error submitting the form.</span>
          </div>
        )
      )}

      {/* Form Section */}
      <form className="mt-1 space-y-2" onSubmit={onSubmit}>
        {/* Form Children */}
        {children}
        {/* Submit button */}
        <div className={`flex flex-col ${buttonAlignClasses[alignButton]}`}>
          <ButtonPrimary type="submit" loading={loading} submit={submit} />
        </div>
      </form>
    </div>
  );
};

export default Form;
