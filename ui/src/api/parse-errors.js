export function parseErrors(err) {
  const errors = err?.response?.data?.errors;

  if (!Array.isArray(errors)) {
    return {
      general: ["Something went wrong."]
    };
  }

  return errors.reduce((result, error) => {
    if (error.attr) {
      result[error.attr] ??= [];
      result[error.attr].push(error.detail);
    } else {
      result.general ??= [];
      result.general.push(error.detail);
    }

    return result;
  }, {});
}