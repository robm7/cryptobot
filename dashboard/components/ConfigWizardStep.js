import React from 'react';

export default function ConfigWizardStep({ title, description, children, isActive }) {
  if (!isActive) return null;

  return (
    <div className="py-6 px-1"> {/* Added some padding */}
      <h2 className="text-2xl font-bold mb-2 text-gray-800">{title}</h2> {/* Increased font size and boldness, changed color */}
      {description && <p className="mb-6 text-gray-600 text-sm">{description}</p>} {/* Increased bottom margin, adjusted text size */}
      <div className="space-y-6"> {/* Added spacing for children elements */}
        {children}
      </div>
    </div>
  );
}