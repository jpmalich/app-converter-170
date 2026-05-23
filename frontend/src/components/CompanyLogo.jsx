import React from "react";

/**
 * Renders either the uploaded company logo, or a hard-coded "W" placeholder.
 * The placeholder picks the letter based on the optional `fallbackText` (first char).
 */
export default function CompanyLogo({ company, size = 36, className = "", testid }) {
  const px = `${size}px`;
  const url = company?.logo_url
    ? `${process.env.REACT_APP_BACKEND_URL}${company.logo_url}`
    : null;
  const letter = (company?.name || "W").trim().charAt(0).toUpperCase();

  if (url) {
    return (
      <img
        src={url}
        alt={company?.name || "Company logo"}
        className={`object-contain bg-[#09090B] ${className}`}
        style={{ width: px, height: px }}
        data-testid={testid}
      />
    );
  }
  return (
    <div
      className={`bg-[#09090B] text-[#F97316] flex items-center justify-center font-heading ${className}`}
      style={{ width: px, height: px, fontSize: size * 0.55 }}
      data-testid={testid}
    >
      {letter}
    </div>
  );
}
